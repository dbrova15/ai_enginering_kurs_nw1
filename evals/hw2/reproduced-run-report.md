# HardwareResearch AI — ДЗ2

Run: `20261117T162104Z-71601edd`

Статус: **provisional — еталони/калібрування не підтверджені**

## Метрики

| Показник | Значення |
| --- | --- |
| abstain | 1.0 |
| abstain_count | 2 |
| agreement | невідомо / incomplete |
| cited | 1.0 |
| cited_count | 18 |
| complete | True |
| correct | 1.0 |
| correct_count | 18 |
| count | 20 |
| failed | 0 |
| faithful | 1.0 |
| faithful_count | 18 |
| false_abstain | 0.0 |
| false_abstain_count | 18 |
| formal_citations | 1.0 |
| formal_citations_count | 73 |
| recall_at_5 | 0.7388888888888889 |

## Retrieval

| Конфігурація | Recall@5 | MRR@5 | N |
| --- | --- | --- | --- |
| hybrid | 0.6393 | 0.7167 | 15 |
| hybrid+rerank | 0.7389 | 0.9333 | 15 |
| vector | 0.7337 | 0.7778 | 15 |

Первинно валідні: 20/20.
Repair: 0.

## Latency

Nearest-rank; секунди. N — кількість фактично виміряних таймерів.

| Етап | N | p50 | p95 |
| --- | --- | --- | --- |
| retrieval_seconds | 20 | 5.0748 | 5.8250 |
| pipeline_seconds | 20 | 9.3513 | 15.2899 |
| evaluation_seconds | 20 | 16.0453 | 25.8512 |

## Витрати

Облік USD цього запуску: 0.02885940.
Окремі components/usage наведено у JSON; одноразовий ingestion/index не включено до 1000 питань.
Нуль зовнішніх витрат для локальних моделей не враховує обладнання й електрику.

## Помилки для розбору

| Компонент | Викликів | Input tokens | Output tokens | USD / 1000 питань |
| --- | --- | --- | --- | --- |
| generator | 20 | 64495 | 5367 | 0.6447 |
| judge | 36 | 69721 | 9178 | 0.7982 |

Екстраполяція з цього N, без індексації, за цінами без cache-знижки; не є рахунком провайдера.

### hr-q19
- Очікуване: 
- Фактичне: {'claims': [], 'limitations': '', 'status': 'not_found'}
- Причина: потребує авторського аналізу доказів; автоматичний verdict збережений у JSON.

### hr-q20
- Очікуване: 
- Фактичне: {'claims': [], 'limitations': '', 'status': 'not_found'}
- Причина: потребує авторського аналізу доказів; автоматичний verdict збережений у JSON.


## Quality gate

- testset_unreviewed
- judge_uncalibrated
- threshold:recall_at_5
- threshold:agreement

## Межі перевірки

- Human review і calibration підтверджуються тільки відповідними артефактами.
- Справжній CI-run потребує user push/PR; локальні тести не підтверджують виконання GitHub Actions.
- Авторське production-рішення й наступні покращення додаються після аналізу помилок.
