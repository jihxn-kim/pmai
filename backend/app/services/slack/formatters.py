"""Block Kit message builders for Slack notifications."""


def format_pr_notification(pr_data: dict, action: str) -> list[dict]:
    emoji = {"opened": "🔀", "closed": "❌", "merged": "✅"}.get(action, "📌")
    title = pr_data.get("title", "")
    number = pr_data.get("number", "")
    author = pr_data.get("user", {}).get("login", "unknown")

    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *PR #{number}* {action} by {author}\n{title}",
            },
        }
    ]


def format_ai_review_notification(summary: str, pr_number: int, score: int | None) -> list[dict]:
    score_text = f" ({score}/10)" if score else ""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🤖 *AI 코드리뷰 완료*: PR #{pr_number}{score_text}\n{summary}",
            },
        }
    ]


def format_deadline_reminder(task_title: str, days: int, is_overdue: bool) -> list[dict]:
    if is_overdue:
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚨 *'{task_title}'* 마감 {days}일 초과",
                },
            }
        ]
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⏰ *'{task_title}'* 내일 마감입니다",
            },
        }
    ]


def format_briefing_notification(org_summary: dict, week_label: str) -> list[dict]:
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📋 주간 브리핑 — {week_label}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": org_summary.get("summary", "브리핑이 생성되었습니다."),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "대시보드에서 상세 내용을 확인하세요.",
            },
        },
    ]


def format_project_status(
    name: str,
    progress: float,
    done: int,
    total: int,
    in_progress: int,
    open_prs: int,
) -> list[dict]:
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📊 {name} 프로젝트 현황"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*진척도:* {progress:.0f}%"},
                {"type": "mrkdwn", "text": f"*완료:* {done}/{total}"},
                {"type": "mrkdwn", "text": f"*진행 중:* {in_progress}"},
                {"type": "mrkdwn", "text": f"*오픈 PR:* {open_prs}"},
            ],
        },
    ]


def format_my_tasks(tasks: list[dict]) -> list[dict]:
    if not tasks:
        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "✨ 할당된 태스크가 없습니다!"},
            }
        ]
    lines = []
    for t in tasks[:10]:
        status_emoji = {
            "todo": "⬜",
            "in_progress": "🔵",
            "review": "🟡",
            "done": "✅",
        }.get(t.get("status", ""), "⬜")
        due = f" (마감: {t['due_date']})" if t.get("due_date") else ""
        lines.append(f"{status_emoji} {t['title']}{due}")
    return [{"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}]


def format_error_message(error: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"죄송합니다. {error}\n\n"
                    "다음과 같은 작업을 도와드릴 수 있어요:\n"
                    "• 프로젝트 진행상황 조회\n"
                    "• 내 태스크 확인\n"
                    "• PR 코드리뷰 요청\n"
                    "• 주간 브리핑 조회\n"
                    "• 프로젝트 문제점 확인\n"
                    "• AI 분석 실행"
                ),
            },
        }
    ]
