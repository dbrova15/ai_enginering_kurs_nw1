# HardwareResearch AI — ДЗ2

Run: `20261124T173746Z-bb92c52b`

Статус: **provisional — еталони/калібрування не підтверджені**

## Метрики

| Показник | Значення |
| --- | --- |
| count | 20 |
| failed | 0 |
| correct | 0.8888888888888888 |
| correct_count | 18 |
| cited | 1.0 |
| cited_count | 18 |
| faithful | 1.0 |
| faithful_count | 18 |
| abstain | 1.0 |
| abstain_count | 2 |
| false_abstain | 0.0 |
| false_abstain_count | 18 |
| formal_citations | 1.0 |
| formal_citations_count | 60 |
| complete | True |
| agreement | невідомо / incomplete |

## Retrieval

| Конфігурація | Recall@5 | MRR@5 | N |
| --- | --- | --- | --- |

Первинно валідні: 20/20.
Repair: 0.

## Latency

Nearest-rank; секунди. N — кількість фактично виміряних таймерів.

| Етап | N | p50 | p95 |
| --- | --- | --- | --- |
| retrieval_seconds | 20 | 13.4963 | 19.0336 |
| pipeline_seconds | 20 | 18.2330 | 24.1036 |
| evaluation_seconds | 20 | 25.4965 | 32.2382 |

## Витрати

Облік USD цього запуску: 0.02636085.
Окремі components/usage наведено у JSON; одноразовий ingestion/index не включено до 1000 питань.
Нуль зовнішніх витрат для локальних моделей не враховує обладнання й електрику.

## Помилки для розбору

| Компонент | Викликів | Input tokens | Output tokens | USD / 1000 питань |
| --- | --- | --- | --- | --- |
| generator | 20 | 64875 | 4285 | 0.6151 |
| judge | 36 | 62772 | 7738 | 0.7029 |

Екстраполяція з цього N, без індексації, за цінами без cache-знижки; не є рахунком провайдера.

### hr-q07
- Очікуване: Робот використовує п’ять цифрових датчиків лінії на модулях ІЧ-відбивача TCRT5000.
- Фактичне: {'status': 'answered', 'claims': [{'text': 'Для створення робота, який їздить по лінії, використовують 5 датчиків лінії.', 'chunk_ids': ['872ca8f4016c9bc27286f680f0988e2c369ba322dd0c6ca59baa97b205c1370e', 'a3598a3218a96557dd7745902c9265efd84fef38a8ae66dbd43705cba32a3049']}], 'limitations': ''}
- Причина: потребує авторського аналізу доказів; автоматичний verdict збережений у JSON.

### hr-q13
- Очікуване: • 448 KB ROM
- Фактичне: {'status': 'answered', 'claims': [{'text': 'ESP32 contains 448 KB of ROM for booting and core functions.', 'chunk_ids': ['6ab9e8cc9d60e3e10cde1fe3b35b8ebde77a4bfd44dc015ec94a8ff8e9720c5a', 'ebaa129235facde9895b8b5865028ed6175ae9fe6bae47f515ac03650a07fa95']}, {'text': 'ESP32-S3 contains 384 KB of ROM for booting and core functions.', 'chunk_ids': ['f3af1dce439117f884c64372136219760aca9e42426648c3ee046a6c7c8ced2f']}], 'limitations': ''}
- Причина: потребує авторського аналізу доказів; автоматичний verdict збережений у JSON.

### hr-q19
- Очікуване: 
- Фактичне: {'status': 'not_found', 'claims': [], 'limitations': ''}
- Причина: потребує авторського аналізу доказів; автоматичний verdict збережений у JSON.

### hr-q20
- Очікуване: 
- Фактичне: {'status': 'not_found', 'claims': [], 'limitations': ''}
- Причина: потребує авторського аналізу доказів; автоматичний verdict збережений у JSON.


## Quality gate

- judge_uncalibrated
- threshold:recall_at_5
- threshold:agreement

## Межі перевірки

- Human review і calibration підтверджуються тільки відповідними артефактами.
- Справжній CI-run потребує user push/PR; локальні тести не підтверджують виконання GitHub Actions.
- Авторське production-рішення й наступні покращення додаються після аналізу помилок.
