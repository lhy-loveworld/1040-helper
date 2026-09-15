"""Synthetic form-field rounding and transfer checks; no taxpayer fixtures."""
import copy
from decimal import Decimal
import importlib.util
from pathlib import Path
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/'1040-helper/scripts'


def load(name):
    spec=importlib.util.spec_from_file_location(name, SCRIPTS/(name+'.py'))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r=load('filing_rounding')
w=load('workflow_checks')


def row(key,amount,action='manual',deps=(),**extra):
    return dict(id=key,amount=amount,action=action,depends_on=list(deps),
                status='calculated',source='Synthetic monetary worksheet',**extra)


class FilingRoundingTests(unittest.TestCase):
    def test_half_up_not_ties_to_even(self):
        for source,result in [('2.49','2'),('2.50','3'),('2.99','3'),('3.50','4'),('0.50','1')]:
            with self.subTest(source=source): self.assertEqual(r.form_dollars(source),result)

    def test_losses_and_negative_zero(self):
        for source,result in [('-2.49','-2'),('-2.50','-3'),('-0.49','0'),('-0.00','0')]:
            with self.subTest(source=source): self.assertEqual(r.form_dollars(source),result)

    def test_combine_receipts_before_rounding_one_entry(self):
        self.assertEqual(r.source_sum_to_form(['10.40','10.40']),'21')
        # Distinct form entries are different from receipt components of one entry.
        self.assertEqual(r.sum_form_dollars([r.form_dollars('10.40'),r.form_dollars('10.40')]),'20')

    def test_calculated_field_uses_rounded_inputs_but_not_rounded_rate(self):
        wage=r.form_dollars('101.60')
        rate=Decimal('0.145')
        result=r.form_dollars(Decimal(wage)*rate)
        self.assertEqual(result,'15')
        self.assertEqual(rate,Decimal('0.145'))

    def test_unknown_propagates_and_empty_sum_is_zero(self):
        self.assertIsNone(r.form_dollars(None))
        self.assertIsNone(r.source_sum_to_form(['10.10',None]))
        self.assertIsNone(r.sum_form_dollars(['10',None]))
        self.assertEqual(r.source_sum_to_form([]),'0')
        self.assertEqual(r.sum_form_dollars([]),'0')

    def test_invalid_known_operand_not_hidden_by_unknown(self):
        for bad in ['NaN','Infinity','bad',1.5,True]:
            with self.subTest(bad=bad), self.assertRaises(ValueError): r.source_sum_to_form([None,bad])
        with self.assertRaises(ValueError): r.sum_form_dollars([None,'1.20'])
        with self.assertRaises(ValueError): r.source_sum_to_form('12.34')

    def test_fractional_form_operand_rejected(self):
        with self.assertRaises(ValueError): r.sum_form_dollars(['10.49','20'])
        self.assertEqual(r.sum_form_dollars(['10.00','-20']),'-10')

    def test_preserve_source_cents(self):
        source=['100.49','200.51']
        snapshot=copy.deepcopy(source)
        self.assertEqual(r.source_sum_to_form(source),'301')
        self.assertEqual(source,snapshot)

    def test_whole_dollar_audit_distinguishes_raw_source_from_form(self):
        rows=[row('raw','10.40','reference'),row('entry','10',deps=['raw'])]
        self.assertTrue(w.check_rows(rows,whole_dollars=True)['internally_consistent'])
        rows[1]['amount']='10.40'
        checked=w.check_rows(rows,whole_dollars=True)
        self.assertIn({'id':'entry','reason':'fractional_form_amount'},checked['issues'])
        self.assertFalse(checked['manual_entries'][0]['ready_for_entry'])

    def test_legacy_cents_audit_is_not_changed(self):
        self.assertTrue(w.check_rows([row('cents','10.40')])['internally_consistent'])
        with self.assertRaises(ValueError): w.check_rows([],whole_dollars='yes')

    def test_gain_chain_reuses_rounded_fields_and_catches_two_dollar_mismatch(self):
        # Each lot has two distinct monetary entry fields, not one net source entry.
        proceeds=r.form_dollars('120.40')
        basis=r.form_dollars('20.60')
        gain=r.form_dollars(Decimal(proceeds)-Decimal(basis))
        schedule_total=r.sum_form_dollars([gain,gain])
        self.assertEqual(schedule_total,'198')
        independently_rounded_raw=r.form_dollars((Decimal('120.40')-Decimal('20.60'))*2)
        self.assertEqual(independently_rounded_raw,'200')
        rows=[row('schedule_d_gain',schedule_total,'calculated'),
              row('main_capital_gain',schedule_total,deps=['schedule_d_gain'],sum_of=['schedule_d_gain']),
              row('other_gain','0'),
              row('investment_gain',r.sum_form_dollars([schedule_total,'0']),
                  deps=['main_capital_gain','other_gain'],sum_of=['main_capital_gain','other_gain'])]
        self.assertTrue(w.check_rows(rows,whole_dollars=True)['internally_consistent'])
        rows[-1]['amount']=independently_rounded_raw
        self.assertIn({'id':'investment_gain','reason':'sum_mismatch'},w.check_rows(rows,whole_dollars=True)['issues'])

    def test_transfer_mismatch_is_not_given_rounding_tolerance(self):
        rows=[row('producer','198','calculated'),row('consumer','199','transfer',['producer'])]
        self.assertIn({'id':'consumer','reason':'transfer_mismatch'},w.check_rows(rows,whole_dollars=True)['issues'])


if __name__=='__main__': unittest.main()
