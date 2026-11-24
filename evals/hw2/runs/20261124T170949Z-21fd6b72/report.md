# HardwareResearch AI — ДЗ2

Run: `20261124T170949Z-21fd6b72`

Статус: **provisional — еталони/калібрування не підтверджені**

## Метрики

| Показник | Значення |
| --- | --- |
| recall_at_5 | 0.8484126984126984 |
| agreement | невідомо / incomplete |

## Retrieval

| Конфігурація | Recall@5 | MRR@5 | N |
| --- | --- | --- | --- |
| vector | 0.8063 | 0.6744 | 15 |
| hybrid | 0.7452 | 0.6722 | 15 |
| hybrid+rerank | 0.8484 | 0.8222 | 15 |

Генерацію та якість відповідей у цьому прогоні не вимірювали.

## Витрати

Облік USD цього запуску: 0 зовнішніх API USD; лише локальний retrieval.
Окремі components/usage наведено у JSON; одноразовий ingestion/index не включено до 1000 питань.
Нуль зовнішніх витрат для локальних моделей не враховує обладнання й електрику.

## Помилки для розбору

Помилки відповідей не вимірювали; retrieval rankings і причини провалу gate наведено окремо.

## Quality gate

- judge_uncalibrated
- eval_incomplete
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
