"""Pure calendar rules for ToDos. Existing fields and task IDs are preserved."""
from datetime import date, timedelta
import copy


def next_occurrence(task, after):
    mode = task.get('repeat')
    if mode == 'daily':
        return after + timedelta(days=1)
    if mode == 'weekly':
        try:
            days = [(date.fromisoformat(task['repeat_anchor']).weekday() + 1) % 7]
        except (KeyError, ValueError, TypeError):
            days = [(after.weekday() + 1) % 7]
    elif mode == 'weekdays':
        values = task.get('repeat_days', [])
        days = [d for d in values if type(d) is int and 0 <= d <= 6] if isinstance(values, list) else []
    else:
        return None
    for offset in range(1, 8):
        candidate = after + timedelta(days=offset)
        if (candidate.weekday() + 1) % 7 in days:
            return candidate
    return None


def normalize_tasks(tasks, cleanup=False, today=None):
    today = today or date.today()
    result = []
    for original in tasks:
        if not isinstance(original, dict):
            result.append(original)
            continue
        task = copy.deepcopy(original)
        try:
            completed = date.fromisoformat(task.get('completed_on', ''))
        except (ValueError, TypeError):
            completed = None
        recurring = task.get('repeat') in ('daily', 'weekly', 'weekdays')
        if task.get('done') and completed and completed <= today:
            if recurring:
                due = next_occurrence(task, completed)
                if due:
                    task['due_on'] = due.isoformat()
                    if due <= today:
                        task['done'] = False
                        task.pop('completed_on', None)
            elif cleanup and completed < today:
                continue
        result.append(task)
    return result
