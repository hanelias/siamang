"""Questionnaire aggregate and validation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from siamang.core.block import Block
from siamang.core.expression import Expression
from siamang.core.page import Page
from siamang.core.question import (
    LikertScale,
    MultiChoice,
    NumericInput,
    Question,
    SingleChoice,
    question_fallback_id,
    question_output_name,
)
from siamang.core.script import _VALID_TRIGGERS
from siamang.core.variable import VariableMap


@dataclass(frozen=True, slots=True)
class LintWarning:
    code: str
    severity: str
    message: str
    location: str | None = None


@dataclass(frozen=True, slots=True)
class Questionnaire:
    title: str
    blocks: list[Question | Block] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)
    deadline: datetime | None = None
    variables: VariableMap | None = None
    scripts: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Questionnaire title must not be empty.")
        if self.blocks and self.pages:
            raise ValueError("Use either 'blocks' or 'pages', not both.")

    def all_questions(self) -> list[Question]:
        if self.pages:
            questions: list[Question] = []
            for page in self.pages:
                questions.extend(page.flatten_questions())
            return questions
        questions: list[Question] = []
        for item in self.blocks:
            if isinstance(item, Block):
                questions.extend(item.flatten_questions())
            else:
                questions.append(item)
        return questions

    def validate(self, strict: bool = False) -> None:
        self._validate_question_ids_and_skip_targets()
        if self.pages:
            page_names: set[str] = set()
            for page in self.pages:
                if not page.name.strip():
                    raise ValueError("Page name must not be empty.")
                if page.name in page_names:
                    raise ValueError(f"Duplicate page name in questionnaire: {page.name}")
                page_names.add(page.name)
            self._validate_page_expressions()
            self._validate_page_expressions_for_export("surveyjs")
            self._validate_page_navigation()
        # Validate scripts
        for script in self.scripts:
            if script.trigger not in _VALID_TRIGGERS:
                raise ValueError(f"Script '{script.name}' has unknown trigger '{script.trigger}'.")
            if script.target:
                all_q_ids = {question_output_name(q) for q in self.all_questions()}
                all_page_names = {p.name for p in (self.pages or [])}
                if script.target not in all_q_ids and script.target not in all_page_names:
                    raise ValueError(
                        f"Script '{script.name}' targets '{script.target}' "
                        f"which is not a known question ID or page name."
                    )
        names: set[str] = set()
        for q in self.all_questions():
            variables = q.var if isinstance(q.var, list) else [q.var]
            for var in variables:
                if var.name in names:
                    raise ValueError(f"Duplicate variable in questionnaire: {var.name}")
                names.add(var.name)
                if self.variables is not None:
                    known = self.variables.require(var.name)
                    if known != var:
                        raise ValueError(f"Variable '{var.name}' differs from registry instance.")
        if strict:
            errors = [issue for issue in self.lint(level="strict") if issue.severity == "error"]
            if errors:
                codes = ", ".join(issue.code for issue in errors)
                raise ValueError(f"Strict questionnaire validation failed: {codes}")

    def _validate_question_ids_and_skip_targets(self) -> None:
        question_ids: set[str] = set()
        duplicates: set[str] = set()
        for question in self.all_questions():
            question_id = question_fallback_id(question)
            if question_id in question_ids:
                duplicates.add(question_id)
            question_ids.add(question_id)
        if duplicates:
            raise ValueError(
                f"Duplicate question id in questionnaire: {', '.join(sorted(duplicates))}"
            )

        page_names = {page.name for page in self.pages}
        known_targets = question_ids | page_names
        for question in self.all_questions():
            if question.skip_to is not None and question.skip_to not in known_targets:
                raise ValueError(
                    f"Question '{question_fallback_id(question)}' skip_to references unknown target: {question.skip_to}"
                )

    def preview(self) -> str:
        return f"Questionnaire<{self.title}> with {len(self.all_questions())} questions"

    def compile(self, **options):
        """Compile to a SurveySchema IR (used by the frontend constructor)."""

        from siamang.frontend.compiler import compile_questionnaire

        return compile_questionnaire(self, options=options or None)

    def deploy(
        self,
        backend: str = "local",
        frontend: str = "local",
        *,
        backend_kwargs: dict | None = None,
        frontend_kwargs: dict | None = None,
        **options,
    ):
        """Compile the survey, provision the backend, build a bundle, publish.

        Returns :class:`siamang.deploy.DeployResult` whose ``collect()`` method
        fetches accumulated responses from the configured backend.
        """

        from siamang.deploy.pipeline import DeployPipeline
        from siamang.deploy.registry import backend_factory, frontend_factory
        from siamang.frontend import FrontendBuilder, ReactRuntime, UIConfig

        backend_cls = backend_factory(backend)
        frontend_cls = frontend_factory(frontend)
        backend_obj = backend_cls(**(backend_kwargs or {}))
        frontend_obj = frontend_cls(**(frontend_kwargs or {}))

        ui = options.pop("ui", None) or UIConfig()
        runtime = options.pop("runtime", None) or ReactRuntime()
        builder = FrontendBuilder(ui=ui, runtime=runtime)
        pipeline = DeployPipeline(backend=backend_obj, frontend=frontend_obj, builder=builder)
        return pipeline.run(self, options=options or None)

    def simulate(self, n: int = 100, seed: int | None = 42):
        from siamang.data.survey_data import SurveyData
        from siamang.local_simulator import simulate_dataframe, simulate_from_pages

        if self.pages:
            frame = simulate_from_pages(self.pages, n=n, seed=seed)
        else:
            frame = simulate_dataframe(self.all_questions(), n=n, seed=seed)
        variables = self.variables or VariableMap()
        if not variables:
            variables = VariableMap()
            for question in self.all_questions():
                vars_in_question = (
                    question.var if isinstance(question.var, list) else [question.var]
                )
                for variable in vars_in_question:
                    if variable.name not in variables:
                        variables.add(variable)
        return SurveyData(frame=frame, variables=variables, questionnaire=self)

    def collect(self):
        raise NotImplementedError(
            "Direct collect() requires a DeployResult. Use survey.deploy(...).collect() "
            "or pass the survey_id / backend to a BackendAdapter explicitly."
        )

    def to_dict(self) -> dict:
        from siamang.core.serialization import question_to_dict

        if self.pages:
            pages = [_page_to_dict(page, question_to_dict) for page in self.pages]
            return {"title": self.title, "pages": pages}
        if self.blocks and all(isinstance(item, Block) for item in self.blocks):
            pages = []
            for index, block in enumerate(self.blocks, start=1):
                assert isinstance(block, Block)
                page_name = _slugify(block.title) if block.title else f"page{index}"
                pages.append(
                    _page_to_dict(
                        Page(name=page_name, title=block.title, items=block.items),
                        question_to_dict,
                    )
                )
            return {"title": self.title, "pages": pages}
        elements = [question_to_dict(q) for q in self.all_questions()]
        return {"title": self.title, "pages": [{"name": "page1", "elements": elements}]}

    def _validate_page_navigation(self) -> None:
        pages = self.pages
        _validate_targets_exist(pages)
        graph = _build_navigation_graph(pages)
        _validate_reachability(pages, graph)
        if _contains_cycle(graph):
            raise ValueError("Cycle detected in page navigation graph.")

    def _validate_page_expressions(self) -> None:
        known_vars = {
            variable.name
            for question in self.all_questions()
            for variable in (question.var if isinstance(question.var, list) else [question.var])
        }
        pattern = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
        probe_answers = {name: 0 for name in known_vars}

        def check(condition, field: str, location: str) -> None:
            if condition is None:
                return
            if not isinstance(condition, (Expression, str)):
                raise ValueError(f"{location} {field} must be str or Expression.")
            if isinstance(condition, Expression):
                referenced = condition.variables()
                expr = condition
            else:
                referenced = set(pattern.findall(condition))
                expr = None
            unknown = referenced - known_vars
            if unknown:
                raise ValueError(
                    f"{location} {field} references unknown variables: {', '.join(sorted(unknown))}"
                )
            if expr is None:
                return
            try:
                expr.validate(known_vars)
                expr.evaluate(probe_answers)
            except Exception as exc:
                raise ValueError(f"{location} has invalid {field} expression.") from exc

        for page in self.pages:
            check(page.show_if, "show_if", f"Page '{page.name}'")
            check(page.hide_if, "hide_if", f"Page '{page.name}'")
            for item in page.items:
                self._check_item_conditions(item, check, f"page '{page.name}'")

        # Blocks attached directly to the questionnaire (blocks mode).
        for item in self.blocks:
            self._check_item_conditions(item, check, "questionnaire")

    @staticmethod
    def _check_item_conditions(item, check, parent: str) -> None:
        from siamang.core.block import Block

        if isinstance(item, Block):
            location = f"Block in {parent}"
            check(item.show_if, "show_if", location)
            check(item.hide_if, "hide_if", location)
            for nested in item.items:
                Questionnaire._check_item_conditions(nested, check, location)
            return
        # Question
        q_id = item.id or item.name or "?"
        location = f"Question '{q_id}' in {parent}"
        check(item.show_if, "show_if", location)
        check(item.hide_if, "hide_if", location)
        choices = getattr(item, "choices", None) or []
        for opt in choices:
            opt_loc = f"Option {opt.code!r} of {location}"
            check(opt.show_if, "show_if", opt_loc)
            check(opt.hide_if, "hide_if", opt_loc)

    def _validate_page_expressions_for_export(self, target: str) -> None:
        if target != "surveyjs":
            raise ValueError(f"Unsupported export target for expression validation: {target}")
        allowed_pattern = re.compile(r"^[\s\w{}<>=!.'&|()\-+*/]+$")
        for page in self.pages:
            if page.show_if is None:
                continue
            expr_text = (
                page.show_if.to_surveyjs()
                if isinstance(page.show_if, Expression)
                else str(page.show_if)
            )
            if not allowed_pattern.match(expr_text):
                raise ValueError(
                    f"Page '{page.name}' show_if contains tokens unsupported by {target}: {expr_text}"
                )

    def validate_for_export(self, target: str = "surveyjs") -> None:
        if self.pages:
            self._validate_page_expressions_for_export(target)
        self.validate()

    def lint(self, level: str = "basic") -> list[LintWarning]:
        if level not in {"basic", "strict"}:
            raise ValueError("lint level must be either 'basic' or 'strict'.")
        warnings: list[LintWarning] = []
        if not self.pages and not self.blocks:
            warnings.append(
                LintWarning(
                    code="EMPTY_QUESTIONNAIRE",
                    severity="warning",
                    message="Questionnaire has no pages or blocks.",
                )
            )
            return warnings
        if self.pages:
            graph = _build_navigation_graph(self.pages)
            for index, page in enumerate(self.pages):
                if not page.items:
                    warnings.append(
                        LintWarning(
                            code="EMPTY_PAGE",
                            severity="error" if level == "strict" else "warning",
                            message=f"Page '{page.name}' has no items.",
                            location=page.name,
                        )
                    )
                implicit_next = _default_successor(self.pages, index)
                if page.default_next is not None and page.default_next == implicit_next:
                    warnings.append(
                        LintWarning(
                            code="REDUNDANT_NAVIGATION",
                            severity="warning",
                            message=(
                                f"Page '{page.name}' has redundant default_next='{page.default_next}' "
                                "(same as implicit order)."
                            ),
                            location=page.name,
                        )
                    )
                if index < len(self.pages) - 1 and not graph[page.name]:
                    warnings.append(
                        LintWarning(
                            code="MISSING_NAVIGATION",
                            severity="warning",
                            message=f"Page '{page.name}' has no outgoing navigation edges.",
                            location=page.name,
                        )
                    )
        if level == "strict":
            warnings.extend(_strict_question_warnings(self.all_questions()))
            if self.variables is not None:
                used = {
                    var.name
                    for question in self.all_questions()
                    for var in _question_variables(question)
                }
                for name in sorted(set(self.variables) - used):
                    warnings.append(
                        LintWarning(
                            code="UNUSED_VARIABLE",
                            severity="warning",
                            message=f"Variable '{name}' is registered but not used in questionnaire.",
                            location=name,
                        )
                    )
        return warnings


def _question_variables(question: Question):
    return question.var if isinstance(question.var, list) else [question.var]


def _strict_question_warnings(questions: list[Question]) -> list[LintWarning]:
    warnings: list[LintWarning] = []
    for question in questions:
        question_id = question_fallback_id(question)
        if question.required and question.show_if is not None:
            warnings.append(
                LintWarning(
                    code="REQUIRED_CONDITIONAL",
                    severity="warning",
                    message=f"Required question '{question_id}' also has conditional visibility.",
                    location=question_id,
                )
            )
        if isinstance(question, NumericInput):
            var = question.var
            if var.scale not in {"interval", "ratio"}:
                warnings.append(
                    LintWarning(
                        code="INCOMPATIBLE_QUESTION_SCALE",
                        severity="error",
                        message=f"NumericInput question '{question_id}' uses non-numeric scale '{var.scale}'.",
                        location=question_id,
                    )
                )
        if isinstance(question, LikertScale):
            var = question.var
            if var.scale != "ordinal":
                warnings.append(
                    LintWarning(
                        code="INCOMPATIBLE_QUESTION_SCALE",
                        severity="error",
                        message=f"LikertScale question '{question_id}' should use ordinal scale, got '{var.scale}'.",
                        location=question_id,
                    )
                )
        if isinstance(question, SingleChoice):
            warnings.extend(_categorical_label_warnings(question_id, [question.var]))
        if isinstance(question, MultiChoice):
            warnings.extend(_categorical_label_warnings(question_id, _question_variables(question)))
    return warnings


def _categorical_label_warnings(question_id: str, variables) -> list[LintWarning]:
    warnings: list[LintWarning] = []
    for var in variables:
        if var.scale in {"nominal", "ordinal"} and not var.labels:
            warnings.append(
                LintWarning(
                    code="CATEGORICAL_WITHOUT_LABELS",
                    severity="error",
                    message=f"Categorical question '{question_id}' variable '{var.name}' has no labels.",
                    location=question_id,
                )
            )
    return warnings


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "page"


def _page_to_dict(page: Page, question_to_dict_fn) -> dict:
    payload = {
        "name": page.name,
        "title": page.title,
        "elements": [question_to_dict_fn(question) for question in page.flatten_questions()],
    }
    if page.randomize_blocks:
        payload["randomizeBlocks"] = True
    if page.show_if is not None:
        payload["visibleIf"] = (
            page.show_if.to_surveyjs()
            if isinstance(page.show_if, Expression)
            else str(page.show_if)
        )
    return payload


def _default_successor(pages: list[Page], index: int) -> str | None:
    if index + 1 >= len(pages):
        return None
    return pages[index + 1].name


def _build_navigation_graph(pages: list[Page]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {page.name: set() for page in pages}
    for index, page in enumerate(pages):
        for _, target in page.next_if:
            graph[page.name].add(target)
        if page.default_next is not None:
            graph[page.name].add(page.default_next)
        else:
            successor = _default_successor(pages, index)
            if successor is not None:
                graph[page.name].add(successor)
    return graph


def _contains_cycle(graph: dict[str, set[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in graph[node]:
            if nxt in graph and dfs(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(dfs(node) for node in graph)


def _iter_targets(page: Page) -> list[str]:
    targets = [target for _, target in page.next_if]
    if page.default_next is not None:
        targets.append(page.default_next)
    return targets


def _validate_targets_exist(pages: list[Page]) -> None:
    known = {page.name for page in pages}
    for page in pages:
        for target in _iter_targets(page):
            if target not in known:
                raise ValueError(f"Unknown target page in navigation: {page.name} -> {target}")


def _validate_reachability(pages: list[Page], graph: dict[str, set[str]]) -> None:
    if not pages:
        return
    start = pages[0].name
    reached: set[str] = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in reached:
            continue
        reached.add(node)
        for nxt in graph[node]:
            stack.append(nxt)
    unreachable = [page.name for page in pages if page.name not in reached]
    if unreachable:
        raise ValueError(f"Unreachable pages in navigation graph: {', '.join(unreachable)}")
