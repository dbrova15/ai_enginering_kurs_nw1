# HardwareResearch AI — порівняльний звіт

Статус: авторська перевірка завершена.

Згенеровано UTC: 2026-10-26T17:39:25.432560+00:00

Етап C виконано після окремого дозволу на 240 первинних генерацій і API-бюджет $0.25. Нових відповідей — 240, фінально валідних — 220, failed — 20. OpenAI: 120/120 валідні одразу; Ollama: 61/120 одразу, 100/120 фінально, 42 repair (39 успішних). Оцінена вартість OpenAI — $0.044028 за фактичні 270244 input / 5819 output tokens; ліміт дотримано. [Протокол і відтворення](results/schema-v2-enums-1/EXPERIMENT_20261026T173328975361Z.md).

Найвищі виміряні aggregate/content accuracy має OpenAI v2, T=0.7: 92.50% / 91.43%. Це спостереження на 10 golden і одному прогоні на конфігурацію; воно не доводить стабільної переваги sampling або промпту.

## Дані й методика

Схема: v2. Golden: 10 документів. Provisional: false.

Контракт генерації: `schema-v2-enums-1`, SHA-256 `716c3e2eb27595c31177e4a6ea391c370a1e0bd8816940fc98e40ef47284a35f`. Результати інших контрактів не включені. Content accuracy — середнє семи полів без language.

Еталон: [golden](data/sourses/hm1/golden.json); SHA-256 `9a3b831cee329deaf1a8175c0a1e581a0fc9e253d2807a27d08b4fab74c71a5a`.

Метрики evaluator й агрегатора повторно звірено з первинними JSONL та їхніми хешами. Конфігурації зіставлено за моделлю, версією/хешем промпту, sampling, схемою, підготовкою та точним набором джерел.

Оцінюється фінальна відповідь після можливого repair. Скалярні поля порівнюються точно, списки — як множини без нормалізації. Missing/failed/invalid дають нуль за всі вісім полів. Aggregate — середнє восьми field accuracy. Метрики списків — micro TP/FP/FN; невизначені частки — н/д.

Новий контракт відхиляє невідомі enum і дублікати: така відповідь невалідна.

## Порівняння конфігурацій

| Модель | Промпт | Sampling | N обробок / golden-порівнянь | Aggregate accuracy (8) | Content accuracy (7) | Валідні до / після repair | Repair | Failed | Повний p50 / p95, с | API USD / 1000 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-4o-mini | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 30 / 10 | 88.75% | 87.14% | 100.00% / 100.00% | 0 (0.00%) | 0 | 1.345762 / 2.335654 | 0.340655 |
| gpt-4o-mini | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 30 / 10 | 91.25% | 90.00% | 100.00% / 100.00% | 0 (0.00%) | 0 | 1.184492 / 1.387156 | 0.341535 |
| gpt-4o-mini | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 30 / 10 | 87.50% | 85.71% | 100.00% / 100.00% | 0 (0.00%) | 0 | 1.312931 / 2.570593 | 0.392415 |
| gpt-4o-mini | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 30 / 10 | 92.50% | 91.43% | 100.00% / 100.00% | 0 (0.00%) | 0 | 1.270024 / 1.869660 | 0.392995 |
| llama3.2:3b | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 30 / 10 | 45.00% | 41.43% | 60.00% / 70.00% | 4 (13.33%) | 9 | 0.888181 / 3.515027 | 0.000000 |
| llama3.2:3b | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 30 / 10 | 65.00% | 61.43% | 50.00% / 100.00% | 15 (50.00%) | 0 | 1.143010 / 1.698925 | 0.000000 |
| llama3.2:3b | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 30 / 10 | 46.25% | 42.86% | 50.00% / 73.33% | 7 (23.33%) | 8 | 1.094338 / 3.835429 | 0.000000 |
| llama3.2:3b | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 30 / 10 | 58.75% | 57.14% | 43.33% / 90.00% | 16 (53.33%) | 3 | 1.145811 / 3.365420 | 0.000000 |

Валідність і час рахуються за всіма записаними обробками, accuracy — лише за golden. Для повторних прогонів знаменник включає повторні спостереження. Н/д означає невідоме, не нуль.

### Accuracy окремих полів

| Модель | Промпт | Sampling | language | primary_topic | mentioned_platforms | mentioned_interfaces | mentions_sensor | mentions_display | mentions_battery | mentions_motor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-4o-mini | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 100.00% | 90.00% | 90.00% | 70.00% | 80.00% | 90.00% | 100.00% | 90.00% |
| gpt-4o-mini | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 100.00% | 90.00% | 90.00% | 70.00% | 100.00% | 90.00% | 100.00% | 90.00% |
| gpt-4o-mini | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 100.00% | 90.00% | 90.00% | 60.00% | 80.00% | 90.00% | 100.00% | 90.00% |
| gpt-4o-mini | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 100.00% | 100.00% | 90.00% | 90.00% | 80.00% | 90.00% | 100.00% | 90.00% |
| llama3.2:3b | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 70.00% | 30.00% | 30.00% | 40.00% | 40.00% | 60.00% | 40.00% | 50.00% |
| llama3.2:3b | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 90.00% | 30.00% | 70.00% | 40.00% | 60.00% | 90.00% | 60.00% | 80.00% |
| llama3.2:3b | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 70.00% | 30.00% | 40.00% | 10.00% | 60.00% | 50.00% | 60.00% | 50.00% |
| llama3.2:3b | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 70.00% | 30.00% | 60.00% | 0.00% | 70.00% | 80.00% | 80.00% | 80.00% |

### Списки: micro precision / recall / F1

| Модель | Промпт | Sampling | Поле | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-4o-mini | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_platforms | 9 | 0 | 1 | 100.00% | 90.00% | 94.74% |
| gpt-4o-mini | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 3 | 0 | 4 | 100.00% | 42.86% | 60.00% |
| gpt-4o-mini | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_platforms | 9 | 0 | 1 | 100.00% | 90.00% | 94.74% |
| gpt-4o-mini | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 3 | 0 | 4 | 100.00% | 42.86% | 60.00% |
| gpt-4o-mini | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_platforms | 9 | 0 | 1 | 100.00% | 90.00% | 94.74% |
| gpt-4o-mini | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 3 | 2 | 4 | 60.00% | 42.86% | 50.00% |
| gpt-4o-mini | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_platforms | 9 | 0 | 1 | 100.00% | 90.00% | 94.74% |
| gpt-4o-mini | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 7 | 1 | 0 | 87.50% | 100.00% | 93.33% |
| llama3.2:3b | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_platforms | 5 | 2 | 5 | 71.43% | 50.00% | 58.82% |
| llama3.2:3b | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 5 | 5 | 2 | 50.00% | 71.43% | 58.82% |
| llama3.2:3b | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_platforms | 8 | 1 | 2 | 88.89% | 80.00% | 84.21% |
| llama3.2:3b | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 2 | 7 | 5 | 22.22% | 28.57% | 25.00% |
| llama3.2:3b | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_platforms | 6 | 1 | 4 | 85.71% | 60.00% | 70.59% |
| llama3.2:3b | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 3 | 16 | 4 | 15.79% | 42.86% | 23.08% |
| llama3.2:3b | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_platforms | 8 | 2 | 2 | 80.00% | 80.00% | 80.00% |
| llama3.2:3b | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 4 | 16 | 3 | 20.00% | 57.14% | 29.63% |

### Перший виклик та usage

| Модель | Промпт | Sampling | Перший p50, с | Перший p95, с | Latency повна | Input tokens | Output tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-4o-mini | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 1.345709 | 2.335608 | True | 62431 | 1425 |
| gpt-4o-mini | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 1.184449 | 1.387117 | True | 62431 | 1469 |
| gpt-4o-mini | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 1.312889 | 2.570540 | True | 72691 | 1448 |
| gpt-4o-mini | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 1.269985 | 1.869618 | True | 72691 | 1477 |
| llama3.2:3b | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 0.835740 | 3.515014 | True | 57685 | 5800 |
| llama3.2:3b | v1 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 0.859603 | 1.679798 | True | 71657 | 3052 |
| llama3.2:3b | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 0.809121 | 3.835415 | True | 75998 | 6023 |
| llama3.2:3b | v2 | {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 0.801486 | 2.975179 | True | 94825 | 4056 |

## Припущення latency та вартості

- Одиниця обліку — записана обробка статті; невдалі обробки входять у знаменники й latency.
- Першу валідність беремо з first_attempt_valid; фінальний успіх повторно перевіряємо за Schema v2.
- Час у секундах; nearest rank: відсортоване значення з номером ceil(p*N). Неповні заміри позначені complete=false.
- first_attempt_seconds включає retry першого виклику; seconds також включає repair й валідацію, без читання TXT та запису JSONL.
- Cold start не позначений у журналах і може входити в latency; це не steady-state benchmark.
- Токени сумуються за журналами разом із repair. Невідомий usage не замінюється нулем; приховані SDK-retry не відновлюються.
- API-вартість — оцінка за повним input-тарифом без кеш-знижки, не рахунок провайдера.
- Лише legacy JSONL не містять provider: для них відповідність model ID тарифу є припущенням; нові витрати враховують явного provider.
- Вартість/1000 — екстраполяція з усіх записаних обробок за незмінних довжин, якості та частоти помилок.
- Для локальної моделі нульові лише зовнішні API-витрати; обладнання та електроенергія не оцінені.
- Повторні файли однієї конфігурації об&#x27;єднуються як повторні спостереження; run_count й unique_documents показують повторення.
- Повністю відсутні в JSONL обробки невідомі: агрегатор не відновлює план експерименту чи перервані до запису запити.
- Accuracy на golden обчислюється окремо через evaluator.py; ці метрики охоплюють усі статті прогону.

### Тарифні припущення

- gpt-4o-mini: {&quot;assumed_provider&quot;: &quot;openai&quot;, &quot;checked_date&quot;: &quot;2026-10-26&quot;, &quot;currency&quot;: &quot;USD&quot;, &quot;input_per_million&quot;: 0.15, &quot;kind&quot;: &quot;external_api&quot;, &quot;output_per_million&quot;: 0.6, &quot;source&quot;: &quot;https://developers.openai.com/api/docs/models/gpt-4o-mini&quot;}.
- llama3.2:3b: {&quot;assumed_provider&quot;: &quot;ollama&quot;, &quot;checked_date&quot;: &quot;2026-10-26&quot;, &quot;currency&quot;: &quot;USD&quot;, &quot;input_per_million&quot;: 0.0, &quot;kind&quot;: &quot;local&quot;, &quot;output_per_million&quot;: 0.0, &quot;source&quot;: &quot;JSONL provider=ollama&quot;}.

## Реальні розбіжності з golden

Автоматично підтверджено розбіжність із еталоном, а не причину її виникнення. Автор має звірити текст і пояснення; сам golden теж може містити помилку.

### 1. HR-0743: mentioned_interfaces

Конфігурація: gpt-4o-mini, промпт v1, sampling {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0}.

Джерело відповіді: [первинний JSONL](results/schema-v2-enums-1/prompt_v1_gpt-4o-mini_t0_20261026T173328975361Z.jsonl).

Доказ для перевірки автором: [текст статті](data/sourses/hm1/texts/en/HR-0743.txt).

Очікуване й фактичне значення:

```json
{
  "expected": [
    "wifi",
    "bluetooth"
  ],
  "actual": []
}
```

**Причина:** У рядку 71 статті прямо названі Wi-Fi® та Bluetooth® у поясненні керування живленням периферії. Підготовлений текст їх зберігає, а відповідь завершена без обриву. Ймовірна причина пропуску — модель звузила витягування до головної теми енергозбереження. Регістр або знак ® могли вплинути, але цей прогін не ізолює їхнього впливу; внутрішня причина не встановлена.

**Висновок:** Це пропуск прямих згадок, який enum-валідація не виявляє: порожній список структурно допустимий. Перевіряти треба всі згадки, включно з поясненнями периферії; причинну гіпотезу про регістр можна перевірити лише окремою контрольованою non-golden пробою.

### 2. HR-0212: primary_topic

Конфігурація: gpt-4o-mini, промпт v1, sampling {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0}.

Джерело відповіді: [первинний JSONL](results/schema-v2-enums-1/prompt_v1_gpt-4o-mini_t0_20261026T173328975361Z.jsonl).

Доказ для перевірки автором: [текст статті](data/sourses/hm1/texts/uk/HR-0212.txt).

Очікуване й фактичне значення:

```json
{
  "expected": "power_batteries",
  "actual": "devices_automation"
}
```

**Причина:** Стаття описує резервне живлення котла від автомобільної АКБ та інвертора, але також докладно пояснює автоматику перемикання реле. Ймовірно, модель надала перевагу способу реалізації — автоматизації — замість предметної мети резервного живлення.

**Висновок:** Обидва класи дозволені схемою; помилка стосується вибору головної теми. Збережений затверджений golden задає power_batteries. Це можливе питання розмітки, але поточні метрики обчислено за незміненим затвердженим еталоном

### 3. HR-0187: mentions_motor

Конфігурація: gpt-4o-mini, промпт v1, sampling {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0}.

Джерело відповіді: [первинний JSONL](results/schema-v2-enums-1/prompt_v1_gpt-4o-mini_t0_20261026T173328975361Z.jsonl).

Доказ для перевірки автором: [текст статті](data/sourses/hm1/texts/uk/HR-0187.txt).

Очікуване й фактичне значення:

```json
{
  "expected": false,
  "actual": true
}
```

**Причина:** У прозі названа помпа, а в коді є int motor = 7 і виклики pinMode/digitalWrite із цим ідентифікатором. Ймовірно, модель використала назву змінної або зв'язок помпи з двигуном як доказ. Правила вимагають явної згадки мотора й не дозволяють робити висновок лише з помпи.

**Висновок:** Підтверджена розбіжність із golden false; називати її безумовною галюцинацією перед уточненням правила некоректно. Назва змінної не дає достатньо аргументів вважати що у статті згаданий двигун. Треба доопрацювати промт.

### 4. HR-0244: mentioned_platforms

Конфігурація: llama3.2:3b, промпт v1, sampling {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0}.

Джерело відповіді: [первинний JSONL](results/schema-v2-enums-1/prompt_v1_llama3.2_3b_t0_20261026T173328975361Z.jsonl).

Доказ для перевірки автором: [текст статті](data/sourses/hm1/texts/uk/HR-0244.txt).

Очікуване й фактичне значення:

```json
{
  "expected": [
    "esp8266"
  ],
  "actual": [
    "esp8266",
    "esp32"
  ]
}
```

**Причина:** Стаття прямо називає Wemos D1 mini на основі ESP8266; пошук по вихідному TXT не знаходить ESP32. Додатковий esp32 не має прямої текстової опори. Можлива причина — змішування споріднених платформ; це припущення, внутрішню причину не встановлено.

**Висновок:** Enum обмежує словник, але дозволений тег усе одно може бути необґрунтованим. Exact-set правильно дає нуль за поле через зайвий esp32; окрема micro-метрика зберігає один TP та один FP. Не слід виводити ESP32 з ESP8266 чи марки Wemos.

### 5. HR-0385: failed

Конфігурація: llama3.2:3b, промпт v1, sampling {&quot;max_tokens&quot;: 512, &quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0}.

Джерело відповіді: [первинний JSONL](results/schema-v2-enums-1/prompt_v1_llama3.2_3b_t0_20261026T173328975361Z.jsonl).

Доказ для перевірки автором: [текст статті](data/sourses/hm1/texts/en/HR-0385.txt).

Очікуване й фактичне значення:

```json
{
  "expected": {
    "language": "en",
    "primary_topic": "devices_automation",
    "mentioned_platforms": [
      "arduino"
    ],
    "mentioned_interfaces": [
      "wifi"
    ],
    "mentions_sensor": true,
    "mentions_display": false,
    "mentions_battery": true,
    "mentions_motor": false
  },
  "actual": null
}
```

**Причина:** Первинна відповідь багаторазово повторює arduino в mentioned_platforms, досягає 512 output tokens і завершується finish_reason=length. Це спостережуваний механізм failure; причина переходу моделі до повторення не встановлена. За чинним конвеєром обрив завершує документ як failed без repair; сирий вміст збережений.

**Висновок:** Немає завершеного об'єкта для оцінювання, тому actual=null і всі вісім полів отримують нуль. Цей випадок не можна подавати як відповідь з першої спроби або виправляти шляхом прихованого повтору. Збільшення max_tokens саме по собі не доводить усунення циклу повторів; зміни промпту чи обробки обриву потребують окремого експерименту.

## Вибір автора для production

Вибір для production OpenAI gpt-4o-mini, v2, T=0.7, top_p=1, max_tokens=512 як кандидата з найвищою виміряною якістю: aggregate 92.50%, content 91.43%, interfaces F1 93.33%, валідність 30/30 без repair, p95 1.87 с, оцінка $0.393 API/1000 таких документів. Ця конфігурація дає найкращий результат при невеликому здорожчанні за додаткові інструкції в промпті
## Умови перегляду рішення

Рішення переглядатиметься, якщо content accuracy знизиться на 2 або більше відсоткових пункти від затвердженого базового рівня. Зміна промпту також є підставою для повторного оцінювання: поточну й нову версії потрібно порівняти на однакових документах, з тим самим golden set і параметрами запуску. Рішення про використання нового промпту прийматиметься за результатами перевірки точності, валідності, затримки та вартості. Базовий content accuracy — 91.43%, поріг перегляду — 89.43% або нижче.

## Обмеження

Результати описують цю вибірку. Один прогін на конфігурацію не доводить статистичної переваги; cold start не відокремлений. Ціни є оцінками за snapshot-тарифами. Джерела з різними входами чи неповними метриками потребують окремого аналізу.

Конкретні умови цієї матриці: max_tokens=512 для обох моделей, SDK retry=0, максимум один repair, Ollama context_length=16384 (підтверджений API). Із 20 failed у локальної моделі 17 почалися з incomplete/length, ще 3 — з невалідного об'єкта та невдалого repair. У всіх 120 OpenAI usage відомий; 120 HTTP-запитів, без repair. Загалом до Ollama — 162 виклики з урахуванням repair; зовнішні API-витрати нульові, обладнання й електрика не оцінені. Перший локальний запит може включати завантаження моделі; окремого warm-up не було. Нові та історичні результати відрізняються контрактом, а також можуть відрізнятися лімітами/контекстом, тому їх не слід зіставляти як чистий ефект зміни промпту.

## Джерела звіту

- [Evaluator JSON](results/evaluation/schema-v2-enums-1/golden_matrix_20261026T173328975361Z.json); SHA-256 `7e067c756a87c071c3825172479d9aeb3ba800f058f34166ce8e0d197d39b185`.
- [Агрегатор JSON](results/metrics/schema-v2-enums-1/runs_matrix_20261026T173328975361Z.json); SHA-256 `2ab45cf6b23e79acf50ad228d0750d25fd9adee390022eb88dcff7ec5e21f2ab`.

