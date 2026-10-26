# HardwareResearch AI — порівняльний звіт

Статус: пройдено авторську перевірку

Згенеровано UTC: 2026-10-26T10:29:32.522332+00:00

## Дані й методика

Схема: v2. Golden: 10 документів. Provisional: false.

Еталон: [golden](data/sourses/hm1/golden.json); SHA-256 `9a3b831cee329deaf1a8175c0a1e581a0fc9e253d2807a27d08b4fab74c71a5a`.

Метрики evaluator й агрегатора повторно звірено з первинними JSONL та їхніми хешами. Конфігурації зіставлено за моделлю, версією/хешем промпту, sampling, схемою, підготовкою та точним набором джерел.

Оцінюється фінальна відповідь після можливого repair. Скалярні поля порівнюються точно, списки — як множини без нормалізації; дублікати тегів не впливають на exact-set. Missing/failed/invalid дають нуль за всі вісім полів. Aggregate — середнє восьми field accuracy. Метрики списків — micro TP/FP/FN; невизначені частки — н/д.

## Порівняння конфігурацій

| Модель | Промпт | Sampling | N обробок / golden-порівнянь | Aggregate accuracy | Валідні до / після repair | Repair | Повний p50 / p95, с | API USD / 1000 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-4o-mini | v1 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 30 / 10 | 76.25% | 100.00% / 100.00% | 0 (0.00%) | 1.118095 / 1.433314 | 0.309005 |
| gpt-4o-mini | v1 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 30 / 10 | 76.25% | 100.00% / 100.00% | 0 (0.00%) | 1.257118 / 2.841971 | 0.309565 |
| gpt-4o-mini | v2 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 30 / 10 | 76.25% | 100.00% / 100.00% | 0 (0.00%) | 1.145220 / 1.668551 | 0.360825 |
| gpt-4o-mini | v2 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 30 / 10 | 75.00% | 100.00% / 100.00% | 0 (0.00%) | 1.230331 / 2.083942 | 0.361305 |
| llama3.2:3b | v1 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 30 / 10 | 60.00% | 100.00% / 100.00% | 0 (0.00%) | 0.639678 / 1.400410 | 0.000000 |
| llama3.2:3b | v1 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 30 / 10 | 61.25% | 100.00% / 100.00% | 0 (0.00%) | 0.687104 / 1.275208 | 0.000000 |
| llama3.2:3b | v2 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 30 / 10 | 65.00% | 100.00% / 100.00% | 0 (0.00%) | 0.565600 / 1.344602 | 0.000000 |
| llama3.2:3b | v2 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 30 / 10 | 61.25% | 100.00% / 100.00% | 0 (0.00%) | 0.624535 / 1.363300 | 0.000000 |

Валідність і час рахуються за всіма записаними обробками, accuracy — лише за golden. Для повторних прогонів знаменник включає повторні спостереження. Н/д означає невідоме, не нуль.

### Accuracy окремих полів

| Модель | Промпт | Sampling | language | primary_topic | mentioned_platforms | mentioned_interfaces | mentions_sensor | mentions_display | mentions_battery | mentions_motor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-4o-mini | v1 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 100.00% | 90.00% | 20.00% | 50.00% | 80.00% | 90.00% | 90.00% | 90.00% |
| gpt-4o-mini | v1 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 100.00% | 90.00% | 20.00% | 50.00% | 80.00% | 90.00% | 100.00% | 80.00% |
| gpt-4o-mini | v2 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 100.00% | 90.00% | 20.00% | 40.00% | 80.00% | 90.00% | 100.00% | 90.00% |
| gpt-4o-mini | v2 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 100.00% | 90.00% | 20.00% | 30.00% | 80.00% | 90.00% | 100.00% | 90.00% |
| llama3.2:3b | v1 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 100.00% | 40.00% | 10.00% | 20.00% | 80.00% | 80.00% | 70.00% | 80.00% |
| llama3.2:3b | v1 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 100.00% | 40.00% | 10.00% | 20.00% | 80.00% | 80.00% | 80.00% | 80.00% |
| llama3.2:3b | v2 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 100.00% | 40.00% | 20.00% | 0.00% | 90.00% | 80.00% | 100.00% | 90.00% |
| llama3.2:3b | v2 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 90.00% | 50.00% | 10.00% | 0.00% | 70.00% | 90.00% | 90.00% | 90.00% |

### Списки: micro precision / recall / F1

| Модель | Промпт | Sampling | Поле | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-4o-mini | v1 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_platforms | 0 | 12 | 10 | 0.00% | 0.00% | 0.00% |
| gpt-4o-mini | v1 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 0 | 7 | 7 | 0.00% | 0.00% | 0.00% |
| gpt-4o-mini | v1 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_platforms | 0 | 15 | 10 | 0.00% | 0.00% | 0.00% |
| gpt-4o-mini | v1 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 0 | 9 | 7 | 0.00% | 0.00% | 0.00% |
| gpt-4o-mini | v2 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_platforms | 0 | 10 | 10 | 0.00% | 0.00% | 0.00% |
| gpt-4o-mini | v2 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 0 | 8 | 7 | 0.00% | 0.00% | 0.00% |
| gpt-4o-mini | v2 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_platforms | 0 | 10 | 10 | 0.00% | 0.00% | 0.00% |
| gpt-4o-mini | v2 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 0 | 12 | 7 | 0.00% | 0.00% | 0.00% |
| llama3.2:3b | v1 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_platforms | 0 | 19 | 10 | 0.00% | 0.00% | 0.00% |
| llama3.2:3b | v1 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 0 | 12 | 7 | 0.00% | 0.00% | 0.00% |
| llama3.2:3b | v1 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_platforms | 0 | 12 | 10 | 0.00% | 0.00% | 0.00% |
| llama3.2:3b | v1 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 0 | 12 | 7 | 0.00% | 0.00% | 0.00% |
| llama3.2:3b | v2 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_platforms | 0 | 10 | 10 | 0.00% | 0.00% | 0.00% |
| llama3.2:3b | v2 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 0 | 18 | 7 | 0.00% | 0.00% | 0.00% |
| llama3.2:3b | v2 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_platforms | 0 | 13 | 10 | 0.00% | 0.00% | 0.00% |
| llama3.2:3b | v2 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | mentioned_interfaces | 0 | 21 | 7 | 0.00% | 0.00% | 0.00% |

### Перший виклик та usage

| Модель | Промпт | Sampling | Перший p50, с | Перший p95, с | Latency повна | Input tokens | Output tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-4o-mini | v1 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 1.118055 | 1.433273 | True | 55801 | 1500 |
| gpt-4o-mini | v1 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 1.257064 | 2.841802 | True | 55801 | 1528 |
| gpt-4o-mini | v2 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 1.145180 | 1.668404 | True | 66061 | 1526 |
| gpt-4o-mini | v2 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 1.230295 | 2.083904 | True | 66061 | 1550 |
| llama3.2:3b | v1 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 0.639633 | 1.400370 | True | 50505 | 2042 |
| llama3.2:3b | v1 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 0.687062 | 1.275165 | True | 50505 | 2020 |
| llama3.2:3b | v2 | {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0} | 0.565560 | 1.344563 | True | 60885 | 1897 |
| llama3.2:3b | v2 | {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0} | 0.624497 | 1.363261 | True | 60885 | 1960 |

## Припущення latency та вартості

- Одиниця обліку — записана обробка статті; невдалі обробки входять у знаменники й latency.
- Першу валідність беремо з first_attempt_valid; фінальний успіх повторно перевіряємо за Schema v2.
- Час у секундах; nearest rank: відсортоване значення з номером ceil(p*N). Неповні заміри позначені complete=false.
- first_attempt_seconds включає retry першого виклику; seconds також включає repair й валідацію, без читання TXT та запису JSONL.
- Cold start не позначений у журналах і може входити в latency; це не steady-state benchmark.
- Токени сумуються за журналами разом із repair. Невідомий usage не замінюється нулем; приховані SDK-retry не відновлюються.
- API-вартість — оцінка за повним input-тарифом без кеш-знижки, не рахунок провайдера.
- Провайдер у первинних JSONL не записаний: відповідність model ID тарифу/локальному запуску є явним припущенням MODEL_PRICING.
- Вартість/1000 — екстраполяція з усіх записаних обробок за незмінних довжин, якості та частоти помилок.
- Для локальної моделі нульові лише зовнішні API-витрати; обладнання та електроенергія не оцінені.
- Повторні файли однієї конфігурації об&#x27;єднуються як повторні спостереження; run_count й unique_documents показують повторення.
- Повністю відсутні в JSONL обробки невідомі: агрегатор не відновлює план експерименту чи перервані до запису запити.
- Accuracy на golden обчислюється окремо через evaluator.py; ці метрики охоплюють усі статті прогону.

### Тарифні припущення

- gpt-4o-mini: {&quot;assumed_provider&quot;: &quot;openai&quot;, &quot;checked_date&quot;: &quot;2026-10-26&quot;, &quot;currency&quot;: &quot;USD&quot;, &quot;input_per_million&quot;: 0.15, &quot;kind&quot;: &quot;external_api&quot;, &quot;output_per_million&quot;: 0.6, &quot;source&quot;: &quot;https://developers.openai.com/api/docs/models/gpt-4o-mini&quot;}.
- llama3.2:3b: {&quot;assumed_provider&quot;: &quot;ollama&quot;, &quot;checked_date&quot;: &quot;2026-10-26&quot;, &quot;currency&quot;: &quot;USD&quot;, &quot;input_per_million&quot;: 0.0, &quot;kind&quot;: &quot;local&quot;, &quot;output_per_million&quot;: 0.0, &quot;source&quot;: &quot;results/sampling_comparison_20261026.md&quot;}.

## Реальні розбіжності з golden

Автоматично підтверджено розбіжність із еталоном, а не причину її виникнення. Автор має звірити текст і пояснення; сам golden теж може містити помилку.

### 1. HR-0743: mentioned_interfaces

Конфігурація: gpt-4o-mini, промпт v1, sampling {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0}.

Джерело відповіді: [первинний JSONL](results/prompt_v1_gpt-4o-mini_20261026T091241044332Z.jsonl).

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

**Причина:** модель могла зосередитися на головній темі енергоспоживання та пропустити другорядні згадки Wi-Fi і Bluetooth у переліку периферії. Точної причини за збереженою відповіддю встановити неможливо .

**Висновок:** потрібно перевіряти повноту витягування другорядних згадок і явно задавати канонічні значення інтерфейсів. Вплив регістру та символу ® окремим експериментом не перевірявся .

### 2. HR-0244: mentioned_platforms

Конфігурація: gpt-4o-mini, промпт v1, sampling {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0}.

Джерело відповіді: [первинний JSONL](results/prompt_v1_gpt-4o-mini_20261026T091241044332Z.jsonl).

Доказ для перевірки автором: [текст статті](data/sourses/hm1/texts/uk/HR-0244.txt).

Очікуване й фактичне значення:

```json
{
  "expected": [
    "esp8266"
  ],
  "actual": [
    "Telegram"
  ]
}
```

**Причина:** Ймовірна причина модель переплутала контекст та сприйняла платформу не в сенсі плати esp8266 а в сенсі меседжера Telegram

**Висновок:** Можливо треба доопрацювати промт бо є вірогідність що модель переплутала контекст та сприйняла платформу не в сенсі плати а в сенсі програмного забеспечення.

### 3. HR-0068: mentions_battery

Конфігурація: gpt-4o-mini, промпт v1, sampling {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0}.

Джерело відповіді: [первинний JSONL](results/prompt_v1_gpt-4o-mini_20261026T091241044332Z.jsonl).

Доказ для перевірки автором: [текст статті](data/sourses/hm1/texts/ru/HR-0068.txt).

Очікуване й фактичне значення:

```json
{
  "expected": false,
  "actual": true
}
```

**Причина:** Ймовірна причина модель не розмежувала загальне джерело живлення та батарею/акумулятор

**Висновок:** в статті є опис живлення від джерела 9 В постійного струму або USB, але батарея чи акумулятор не згадуються. Тому очікуване значення mentions_battery=false

### 4. HR-0212: primary_topic

Конфігурація: gpt-4o-mini, промпт v1, sampling {&quot;temperature&quot;: 0.0, &quot;top_p&quot;: 1.0}.

Джерело відповіді: [первинний JSONL](results/prompt_v1_gpt-4o-mini_20261026T091241044332Z.jsonl).

Доказ для перевірки автором: [текст статті](data/sourses/hm1/texts/uk/HR-0212.txt).

Очікуване й фактичне значення:

```json
{
  "expected": "power_batteries",
  "actual": "devices_automation"
}
```

**Причина:** Ймовірна причина неправильно визначено тему статті через хибне трактування загальної ідеї.

**Висновок:** тема статті альтернативне джерело живлення а саме кастомна зарядна станція, але модель визначила що це прибор для автоматизації через принцип роботи зарядної станції коли вона перемикається з живлення від мережі на акомулятор та назад.

### 5. HR-0227: language

Конфігурація: llama3.2:3b, промпт v2, sampling {&quot;temperature&quot;: 0.7, &quot;top_p&quot;: 1.0}.

Джерело відповіді: [первинний JSONL](results/prompt_v2_llama3.2_3b_20261026T095513809612Z.jsonl).

Доказ для перевірки автором: [текст статті](data/sourses/hm1/texts/uk/HR-0227.txt).

Очікуване й фактичне значення:

```json
{
  "expected": "uk",
  "actual": "ru"
}
```

**Причина:** Можливо модель побачивши кирилицю зупинила вибір на російській не роблячи глибше дослідження

**Висновок:** Цей приклад показує помилку розпізнавання української мови. Потрібна окрема перевірка визначення мови на українських і російських текстах; внутрішню причину помилки не встановлено

## Вибір автора для production

Модель gpt-4o-mini однаково впоралася з промптами обох версій з температурою 0. трохи гірше з промптом v2 та температурою 0.7. Тому мій вибір для продакшену  gpt-4o-mini промт v1 та температура 0 як найточніший варіант та дешевший через менший промпт.

## Умови перегляду рішення

Рішення переглядатиметься у разі зміни обраної моделі, її доступності або тарифів, а також появи моделі-кандидата з кращим співвідношенням якості, затримки та вартості. Повторне оцінювання потрібне при зміні схеми, промпту, правил підготовки тексту або складу корпусу — наприклад, додаванні нових мов чи типів статей. Окремою підставою є регулярні помилки у важливих полях, зростання частоти repair або перевищення прийнятної затримки й бюджету. Нову конфігурацію буде обрано після порівняння на однакових документах із вручну перевіреним golden set. Особливу увагу при перегляді рішення приділятиму точності mentioned_platforms і mentioned_interfaces, оскільки поточні результати показують проблеми з цими полями.

## Обмеження

Результати описують цю вибірку. Один прогін на конфігурацію не доводить статистичної переваги; cold start не відокремлений. Ціни є оцінками за snapshot-тарифами. Джерела з різними входами чи неповними метриками потребують окремого аналізу.

## Джерела звіту

- [Evaluator JSON](results/evaluation/golden_20261026T095934403348Z.json); SHA-256 `51d9268f40aabd912cc1dc6b4f9b567520d81c9934049fde5aefd41bcf212b51`.
- [Агрегатор JSON](results/metrics/runs_20261026T101448227707Z.json); SHA-256 `3449e8af92e45458ead98619e71d0dde2df436e6c463e851e9bc2aeb0f0aa21f`.

