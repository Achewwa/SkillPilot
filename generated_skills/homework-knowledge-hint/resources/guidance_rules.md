# Guidance Rules

## Purpose

Use this skill to help Claude handle: 我想要一个 Skill，根据课程课件给书面作业题生成知识点提示，但不能直接给答案。 It turns the user's vague need into a structured workflow, safe boundaries, and reusable output templates.

## Required Boundaries

- Do not provide a complete homework answer; guide the user with concepts and steps.
- Do not install third-party extensions, run shell commands, or request secrets.
- Do not invent source material that the user has not provided.
- Prefer safe guidance, checklists, templates, and examples over direct high-risk automation.

## Workflow Reminders

1. Restate the user's goal and identify the relevant task context.
2. Ask for missing details only when the task cannot be handled safely from the current context.
3. Apply the rules and templates in resources/ before producing the final response.
4. Generate the response in the requested output format.
5. Review the response against the constraints and remove unsafe or overreaching content.
