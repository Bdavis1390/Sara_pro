import unittest
from gandhari_revision_benchmark import (
    RevisionCase,
    RevisionClass,
    adjudication_target,
    survival_label,
)

class GandhariRevisionBenchmarkTests(unittest.TestCase):
    def test_orthographic_change_is_nonmaterial(self):
        c = RevisionCase("x","a","ā",RevisionClass.ORTHOGRAPHIC_NONMATERIAL)
        self.assertEqual(c.materiality(),"NONMATERIAL")
        self.assertEqual(
            c.translation_action(),
            "NO_REAUDIT_REQUIRED_ON_THIS_CHANGE",
        )

    def test_named_entity_change_triggers_reaudit_when_dependency_exists(self):
        c = RevisionCase(
            "x","old","new",RevisionClass.NAMED_ENTITY,
            translation_dependency_found=True,
        )
        self.assertEqual(c.translation_action(),"REAUDIT_DEPENDENT_TRANSLATION")

    def test_missing_dependency_requires_search(self):
        c = RevisionCase("x","old","new",RevisionClass.LEXICAL)
        self.assertEqual(c.translation_action(),"DEPENDENCY_SEARCH_REQUIRED")

    def test_semantic_survival_is_separate_from_source_change(self):
        self.assertEqual(
            survival_label("king","king"),
            "SEMANTICS_SURVIVE_REVISION",
        )
        self.assertEqual(
            survival_label("king","prince"),
            "SEMANTICS_CHANGED_AFTER_REVISION",
        )

if __name__ == "__main__":
    unittest.main()
