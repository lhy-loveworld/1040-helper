"""Synthetic workflow invariants. No taxpayer data or real tax-limit fixtures."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workflow_checks', ROOT/'1040-helper/scripts/workflow_checks.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def row(key, amount, action='manual', deps=(), status='calculated', **extra):
    return dict(id=key, amount=amount, action=action, depends_on=list(deps),
                status=status, source='Synthetic worksheet', **extra)


def entry(key, amount, year, kind='employer', participant='owner'):
    return dict(id=key, amount=amount, year=year, kind=kind, participant=participant,
                deposit_date='2031-02-03', evidence='Synthetic statement',
                year_evidence='Synthetic designation' if year else None)


class WorkflowTests(unittest.TestCase):
    def base_rows(self):
        return [row('se_half','100','reference'),
                row('adjustment_se','100','transfer',['se_half']),
                row('retirement','900'),
                row('total_adjustments','1000','calculated',['adjustment_se','retirement'],
                    sum_of=['adjustment_se','retirement'])]

    def test_manual_deduction_present_but_automatic_total_not_in_checklist(self):
        result = w.check_rows(self.base_rows())
        self.assertEqual([x['id'] for x in result['manual_entries']], ['retirement'])
        self.assertTrue(result['manual_entries'][0]['ready_for_entry'])
        self.assertTrue(result['internally_consistent'])
        self.assertFalse(result['tax_validated'])

    def test_missing_retirement_dependency_fails(self):
        rows = [r for r in self.base_rows() if r['id'] != 'retirement']
        with self.assertRaises(ValueError): w.check_rows(rows)

    def test_unknown_not_zero_or_ready(self):
        rows = self.base_rows()
        rows[2].update(amount=None, status='unknown')
        result = w.check_rows(rows)
        self.assertIsNone(result['manual_entries'][0]['amount'])
        self.assertFalse(result['manual_entries'][0]['ready_for_entry'])
        self.assertIn({'id':'total_adjustments','reason':'unresolved_dependency'},result['issues'])

    def test_conditional_known_amount_blocks_downstream(self):
        rows = self.base_rows()
        rows[2]['status']='conditional'
        self.assertFalse(w.check_rows(rows)['manual_entries'][0]['ready_for_entry'])

    def test_wrong_sum_and_transfer_detected(self):
        rows = self.base_rows()
        rows[1]['amount']='101'
        reasons={i['reason'] for i in w.check_rows(rows)['issues']}
        self.assertTrue({'transfer_mismatch','sum_mismatch'}.issubset(reasons))

    def test_reconfirmation_no_change_and_replacement_affects_dependents(self):
        rows=[row('expense','200','reference'),row('profit','800','calculated',['expense']),
              row('tax','80','calculated',['profit'])]
        original=copy.deepcopy(rows)
        self.assertEqual(w.affected_lines(rows,[]),[])
        rows[0]['amount']='250'  # Replace same ID; not a second expense.
        self.assertEqual(len(rows),len(original))
        self.assertEqual(w.affected_lines(rows,['expense']),['expense','profit','tax'])

    def test_transitive_qbi_and_refund_invalidation_order_independent(self):
        rows=[row('refund','10','calculated',['tax']),row('tax','90','calculated',['taxable']),
              row('taxable','900','calculated',['agi','qbi']),
              row('qbi','100','calculated',['retirement','profit']),
              row('agi','1000','calculated',['retirement','profit','wages']),
              row('wages','500','reference'),row('profit','700','reference'),row('retirement','200')]
        self.assertEqual(w.affected_lines(rows,['retirement']),
                         ['agi','qbi','refund','retirement','tax','taxable'])

    def test_cycles_duplicates_and_bad_money_fail(self):
        for rows in ([row('a','1',deps=['b']),row('b','1',deps=['a'])],
                     [row('a','1'),row('a','2')], [row('a','NaN')],
                     [row('a',1.2)], [row('a','Infinity')]):
            with self.subTest(rows=rows), self.assertRaises(ValueError): w.check_rows(rows)

    def test_mixed_revisions_detected(self):
        self.assertEqual(w.check_revisions('r2',{'json':'r2','markdown':'r1','trace':'r1'}),['markdown','trace'])
        self.assertEqual(w.check_revisions('r2',{'json':'r2','markdown':'r2'}),[])

    def test_combined_employer_year_is_not_inferred_from_deposit_or_residual(self):
        before=[entry('old','8000',2030)]
        after=[entry('employee','6000',2031,'employee'),entry('combined','2000',None)]
        result=w.reconcile_contributions(before,after)
        self.assertEqual(result['principal_difference'],'0')
        self.assertFalse(result['allocation_complete'])
        self.assertEqual(result['after']['unresolved_ids'],['combined'])
        self.assertEqual(len(result['after']['buckets']),1)

    def test_explicit_split_reconciles_without_claiming_tax_validity(self):
        before=[entry('old','8000',2030)]
        after=[entry('employee','6000',2031,'employee'),entry('prior','700',2030),entry('next','1300',2031)]
        result=w.reconcile_contributions(before,after)
        self.assertTrue(result['allocation_complete'])
        self.assertEqual(result['principal_difference'],'0')
        self.assertEqual(len(result['after']['buckets']),3)
        self.assertFalse(result['tax_validated'])

    def test_nonzero_difference_requires_explanation_not_silent_balancing(self):
        result=w.reconcile_contributions([entry('old','8000',2030)],[entry('new','7900',2030)])
        self.assertEqual(result['principal_difference'],'-100')

    def test_year_evidence_and_valid_principal_required(self):
        bad=entry('a','100',2030)
        bad['year_evidence']=None
        for entries in ([bad],[entry('a','-100',2030)], [entry('a','100',2030),entry('a','100',2030)]):
            with self.assertRaises(ValueError): w.reconcile_contributions([],entries)

    def test_participants_not_merged_and_inputs_not_mutated(self):
        entries=[entry('a','100',2030,participant='one'),entry('b','200',2030,participant='two')]
        original=copy.deepcopy(entries)
        result=w.reconcile_contributions(entries,entries)
        self.assertEqual(len(result['after']['buckets']),2)
        self.assertEqual(entries,original)


if __name__ == '__main__': unittest.main()
