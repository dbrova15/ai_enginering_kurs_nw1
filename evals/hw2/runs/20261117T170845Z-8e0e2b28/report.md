# HardwareResearch AI — ДЗ2

Run: `20261117T170845Z-8e0e2b28`

Статус: **provisional — еталони/калібрування не підтверджені**

## Метрики

| Показник | Значення |
| --- | --- |
| recall_at_5 | 0.7388888888888889 |
| agreement | невідомо / incomplete |

## Retrieval

| Конфігурація | Recall@5 | MRR@5 | N |
| --- | --- | --- | --- |
| vector | 0.7337 | 0.7778 | 15 |
| hybrid | 0.6393 | 0.7167 | 15 |
| hybrid+rerank | 0.7389 | 0.9333 | 15 |

Генерацію та якість відповідей у цьому прогоні не вимірювали.

## Витрати

Облік USD цього запуску: 0 зовнішніх API USD; лише локальний retrieval.
Окремі components/usage наведено у JSON; одноразовий ingestion/index не включено до 1000 питань.
Нуль зовнішніх витрат для локальних моделей не враховує обладнання й електрику.

## Помилки для розбору

Помилки відповідей не вимірювали; retrieval rankings і причини провалу gate наведено окремо.

## Quality gate

- testset_unreviewed
- judge_uncalibrated
- eval_incomplete
- threshold:recall_at_5
- threshold:correct
- threshold:cited
- threshold:faithful
- threshold:abstain
- threshold:formal_citations
- threshold:agreement

## Межі перевірки

- Human review і calibration підтверджуються тільки відповідними артефактами.
- Справжній CI-run потребує user push/PR; локальні тести не підтверджують виконання GitHub Actions.
- Авторське production-рішення й наступні покращення додаються після аналізу помилок.
