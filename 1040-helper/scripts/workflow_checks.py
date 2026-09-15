"""Pure bookkeeping checks for filing references, NOT tax-law validation.

See references/filing-handoff.md for the input contract. No files are changed.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation


def money(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Money must be a decimal string')
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('Invalid decimal amount') from exc
    if not result.is_finite():
        raise ValueError('Money must be finite')
    return result


def _index(rows):
    indexed = {}
    for row in rows:
        key = row.get('id')
        if not isinstance(key, str) or not key or key in indexed:
            raise ValueError('Missing or duplicate row ID')
        if row.get('action') not in {'manual', 'transfer', 'calculated', 'reference'}:
            raise ValueError('Invalid action')
        if row.get('status') not in {'confirmed', 'calculated', 'conditional', 'unknown'}:
            raise ValueError('Invalid status')
        if not isinstance(row.get('source'), str) or not row['source'].strip():
            raise ValueError('Source provenance is required')
        if row.get('amount') is not None:
            money(row['amount'])
        deps = row.get('depends_on', [])
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            raise ValueError('Dependencies must be a list of row IDs')
        if len(set(deps)) != len(deps):
            raise ValueError('Duplicate dependency')
        sums = row.get('sum_of', [])
        if not isinstance(sums, list) or not all(isinstance(d, str) for d in sums):
            raise ValueError('sum_of must be a list of row IDs')
        if len(set(sums)) != len(sums) or not set(sums).issubset(deps):
            raise ValueError('Sum operands must be distinct dependencies')
        indexed[key] = row
    visiting, visited = set(), set()

    def visit(key):
        if key not in indexed:
            raise ValueError('Missing dependency: ' + key)
        if key in visiting:
            raise ValueError('Dependency cycle')
        if key in visited:
            return
        visiting.add(key)
        for parent in indexed[key].get('depends_on', []):
            visit(parent)
        visiting.remove(key)
        visited.add(key)

    for key in indexed:
        visit(key)
    return indexed


def affected_lines(rows, changed_ids):
    indexed = _index(rows)
    affected = set(changed_ids)
    if not affected.issubset(indexed):
        raise ValueError('Changed ID not present in reference')
    while True:
        expanded = affected | {key for key, row in indexed.items()
                               if affected.intersection(row.get('depends_on', []))}
        if expanded == affected:
            return sorted(affected)
        affected = expanded


def check_rows(rows, *, whole_dollars=False):
    if type(whole_dollars) is not bool:
        raise ValueError('whole_dollars must be a boolean')
    indexed = _index(rows)
    issues, blocked = [], set()
    for key, row in indexed.items():
        if whole_dollars and row['action'] != 'reference' and row.get('amount') is not None:
            amount = money(row['amount'])
            if amount != amount.to_integral_value():
                blocked.add(key)
                issues.append({'id': key, 'reason': 'fractional_form_amount'})
        if row.get('amount') is None or row['status'] in {'conditional', 'unknown'}:
            blocked.add(key)
            issues.append({'id': key, 'reason': 'unresolved_input'})
        operands = row.get('sum_of', [])
        if operands and all(indexed[d].get('amount') is not None for d in operands):
            expected = sum((money(indexed[d]['amount']) for d in operands), Decimal(0))
            if row.get('amount') is not None and money(row['amount']) != expected:
                blocked.add(key)
                issues.append({'id': key, 'reason': 'sum_mismatch'})
        if row['action'] == 'transfer':
            deps = row.get('depends_on', [])
            if len(deps) != 1:
                raise ValueError('A transfer needs exactly one source row')
            parent = indexed[deps[0]].get('amount')
            if parent is not None and row.get('amount') is not None and money(parent) != money(row['amount']):
                blocked.add(key)
                issues.append({'id': key, 'reason': 'transfer_mismatch'})
    downstream = set(affected_lines(rows, blocked))
    for key in sorted(downstream - blocked):
        issues.append({'id': key, 'reason': 'unresolved_dependency'})
    manual = []
    for key, row in indexed.items():
        if row['action'] == 'manual':
            entry = deepcopy(row)
            # Readiness means internally consistent supplied data, not legal approval.
            entry['ready_for_entry'] = key not in downstream
            manual.append(entry)
    return {'issues': issues, 'manual_entries': manual,
            'internally_consistent': not issues, 'tax_validated': False}


def check_revisions(current_revision, artifact_revisions):
    if not isinstance(current_revision, str) or not current_revision:
        raise ValueError('Current revision is required')
    return sorted(name for name, revision in artifact_revisions.items()
                  if revision != current_revision)


def _snapshot(entries):
    seen, buckets, unresolved = set(), {}, []
    total = Decimal(0)
    for entry in entries:
        key = entry.get('id')
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError('Missing or duplicate contribution ID')
        seen.add(key)
        for field in ('participant', 'evidence', 'deposit_date'):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError('Missing contribution ' + field)
        try:
            date.fromisoformat(entry['deposit_date'])
        except ValueError as exc:
            raise ValueError('Invalid deposit date') from exc
        amount = money(entry.get('amount'))
        if amount < 0:
            raise ValueError('Snapshot contributions cannot be negative postings')
        kind, year = entry.get('kind'), entry.get('year')
        if kind not in {'employee', 'employer', 'unknown'}:
            raise ValueError('Invalid contribution source')
        if year is not None:
            if type(year) is not int or not 1900 <= year <= 9999:
                raise ValueError('Invalid contribution year')
            if not isinstance(entry.get('year_evidence'), str) or not entry['year_evidence'].strip():
                raise ValueError('Known contribution year requires evidence')
        total += amount
        if year is None or kind == 'unknown':
            unresolved.append(key)
        else:
            bucket = (entry['participant'], year, kind)
            buckets[bucket] = buckets.get(bucket, Decimal(0)) + amount
    return {'total': str(total), 'unresolved_ids': unresolved,
            'buckets': [{'participant': who, 'year': year, 'kind': kind, 'amount': str(amount)}
                        for (who, year, kind), amount in sorted(buckets.items())]}


def reconcile_contributions(before, after):
    old, new = _snapshot(before), _snapshot(after)
    difference = money(new['total']) - money(old['total'])
    return {'before': old, 'after': new, 'principal_difference': str(difference),
            'allocation_complete': not old['unresolved_ids'] and not new['unresolved_ids'],
            'tax_validated': False}
