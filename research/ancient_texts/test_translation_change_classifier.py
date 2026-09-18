import unittest
from translation_change_classifier import (
    ReauditState,
    ChangedReading,
    classify_changed_reading,
    named_entity_change,
)

class TranslationChangeClassifierTests(unittest.TestCase):
    def test_current_name_resolves_candidate(self):
        change = named_entity_change(
            "p.oxy.1.51",
            "Isidoros",
            "Klaudianos",
            "Isidoros",
        )
        self.assertEqual(
            classify_changed_reading(change),
            ReauditState.RESOLVED_CURRENT_ON_AUDITED_CHANGE,
        )

    def test_old_name_confirms_stale(self):
        change = named_entity_change(
            "p.tebt.2.408",
            "Hipponikos",
            "Hippolitos",
            "Hippolitos",
        )
        self.assertEqual(
            classify_changed_reading(change),
            ReauditState.CONFIRMED_STALE,
        )

    def test_unmatched_form_remains_unresolved(self):
        change = ChangedReading(
            "x","alpha","beta","gamma","LEXICAL",True
        )
        self.assertEqual(
            classify_changed_reading(change),
            ReauditState.MATERIAL_CHANGE_TRANSLATION_UNRESOLVED,
        )

    def test_nonmaterial_change_does_not_trigger_staleness(self):
        change = ChangedReading(
            "x","orth1","orth2","semantic equivalent","ORTHOGRAPHY",False
        )
        self.assertEqual(
            classify_changed_reading(change),
            ReauditState.NONMATERIAL_CHANGE,
        )

if __name__ == "__main__":
    unittest.main()
