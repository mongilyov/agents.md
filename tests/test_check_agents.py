import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import check_agents as check

class CheckTests(unittest.TestCase):
    def setUp(self):
        self.template='Rules\n<!-- BEGIN PROJECT SETTINGS -->\n- Setup confirmed: no\n- Repo: `<OWNER/REPO>`\n<!-- END PROJECT SETTINGS -->\nMore rules\n'
        self.configured=self.template.replace('confirmed: no','confirmed: yes').replace('<OWNER/REPO>','owner/repo')
    def test_only_settings_may_change(self):
        check.validate(self.template,self.configured)
    def test_setup_must_be_confirmed(self):
        with self.assertRaises(ValueError): check.validate(self.template,self.template)
        check.validate(self.template,self.template,allow_unconfigured=True)
    def test_placeholders_rejected_even_after_confirmation(self):
        with self.assertRaises(ValueError): check.validate(self.template,self.template.replace('confirmed: no','confirmed: yes'))
    def test_shared_edits_rejected_even_in_setup(self):
        for s in [self.configured.replace('More rules','Fewer rules'),self.configured+'extra',self.configured.replace('Rules\n','')]:
            with self.assertRaises(ValueError): check.validate(self.template,s,allow_unconfigured=True)
    def test_markers_must_be_unique_and_ordered(self):
        for s in [self.configured.replace(check.END,''),self.configured+check.BEGIN,self.configured.replace(check.BEGIN,'TEMP').replace(check.END,check.BEGIN).replace('TEMP',check.END)]:
            with self.assertRaises(ValueError): check.validate(self.template,s)
    def test_settings_fields_cannot_be_removed_or_added(self):
        for s in [self.configured.replace('- Repo: `owner/repo`\n',''),self.configured.replace('- Repo: `owner/repo`','- Repo: '),self.configured.replace('- Repo:', '- Extra: bypass\n- Repo:')]:
            with self.assertRaises(ValueError): check.validate(self.template,s)

    def test_duplicate_confirmation_rejected(self):
        s=self.configured.replace('- Setup confirmed: yes','- Setup confirmed: yes\n- Setup confirmed: no')
        with self.assertRaises(ValueError): check.validate(self.template,s)
if __name__=='__main__': unittest.main()
