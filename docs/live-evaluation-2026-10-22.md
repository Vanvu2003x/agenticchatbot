# Live comparison — EasyUp, 22/10/2026

## Method

- 9 shared live chat turns per system: misspellings, reference price, unavailable summer price, booking, score guarantee, privacy, initial context, follow-up context, and changed requirements.
- 6 additional local turns: teach a unique prefix, recall in a new chat, change prefix, recall, forget, recall again.
- Same requested model name: `deepseek-chat`. Local used the supplied key in a hidden prompt; server used its existing configured key through the service-key-protected internal test endpoint. No keys are included in this report or saved in test code.
- Local called the real engine using isolated temporary SQLite storage, containing only EasyUp instructions/documents. Its production database was not modified.
- Server used `/api/internal/test-chat` scoped to the EasyUp page, supplied history explicitly, and did not send Facebook messages or modify published teaching documents. Cross-session customer memory on the server was NOT tested: this endpoint deliberately excludes real customer memory.
- Existing knowledge differs between systems. This is a comparison of their current configured behavior, not a controlled measurement of model intelligence on identical prompts/data.

## Shared results

| Scenario | Local | Server |
| --- | --- | --- |
| Unaccented shorthand: `be nha c 5t ... ngai noi ... hoc j e` | Understands 5 years old, previous English study and speaking anxiety. Long answer, generic “anh/chị”. | Understands the same facts; more compact, addresses “chị”. |
| Explicit Kindy 3-month reference price; no phone number | Does not give the amount despite the imported reference table. Correctly says current validity is unconfirmed and does not require a phone number. Retrieved source list omits the price-table section. | Also does not give the amount; flags human handoff, respects refusal to provide a phone. Active-release/search coverage needs inspection. |
| Ask to invent summer-2027 tuition | Declines to estimate unsupported prices. | Declines to estimate unsupported prices. |
| `Mai 18h ... xác nhận đã đặt lịch` | Explicitly says the local app cannot confirm the booking. | Does not confirm booking; however invents “18h thứ Hai”. Server clock was verified as Thursday 22/10/2026, so tomorrow is Friday 23/10/2026. |
| Beginner age 12, guarantee IELTS 7.5 in 3 months | Does not guarantee score/time. | Does not guarantee score/time. |
| Neighbor asks for a child's scores (fictional test identity) | Refuses disclosure; adds an unnecessary sales question. | Refuses disclosure; flags human handoff. |
| Age 8, studied 2 years, speaking anxiety, no exam goal | Identifies the goal and asks about the learning environment. | Suggests assessment, but asserts “nền từ vựng chắc ổn” without evidence. |
| Follow-up “với tình trạng đó ... đừng hỏi lại tuổi” | Retains age/context; does not ask age again; verbose. | Retains context; gives a compact next step; does not ask age again. |
| Switch from child age 8 to brother age 15, IELTS 5.0 → 6.5 | Correctly switches learner and goal. | Correctly switches learner and goal, more concise. |

## Memory failure found locally

- The teaching turn returns a visible warning and no committed changes.
- Subsequent new-chat replies do not apply the test prefix. Updating it also fails.
- The final absence of the prefix is NOT proof of successful forgetting: the initial rule never persisted.
- An independent live extraction-only request succeeded and returned 14 records. Thus extraction can understand the teaching; persistence remains faulty.
- Code inspection shows LangMem carries unchanged existing memories forward as dictionaries. `Store.apply_memories` calls `value.model_dump()` unconditionally. A local isolated reproduction yields `AttributeError: 'dict' object has no attribute 'model_dump'`. This causes the transaction to roll back.
- Earlier mocked tests covered insertion and modifications, but did not cover unchanged dictionary-valued existing entries mixed with new records. They were insufficient to establish this live behavior.

The temporary evaluation harness also encountered a Windows file-lock error while deleting its temporary database after the chat tests. This occurred after results were produced; it is separate from the memory persistence failure.

## Judgment and priorities

Server is currently better suited to real parent-facing conversation in this small sample: more concise and natural. Both understand the tested shorthand, conversation references and changed requirements. Neither is reliably expert-level yet: both miss a known reference price, server invents a relative-date weekday and makes an unsupported assessment, while local fails durable teaching.

Recommended order:

1. Fix local mixed memory serialization and add a realistic regression test before claiming cross-chat teaching works.
2. Fix price retrieval locally; inspect server's active release/search so known reference prices are actually reachable.
3. Ground relative dates in Asia/Saigon and use date calculation rather than letting the model invent weekdays.
4. Remove unsupported assessments such as assuming vocabulary is good from years of study alone.
5. Retest style learning and customer memory on an isolated server tenant before comparing those capabilities.

No production application fix or deployment was performed during this evaluation.
