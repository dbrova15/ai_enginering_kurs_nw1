# Ручна перевірка Golden Set v2

Статус: **10/10 approved**. Людська перевірка виконана автором проєкту; рішення нижче збережено дослівно. Первинну чернетку підготував агент за TXT.
Старий golden використано тільки для звірки ID; старі expected і модельні runs не використані для отримання міток.
Рядки посилаються на первинний TXT. Видалений header не є доказом. Reviewer: автор проєкту (користувач цієї сесії); reviewed_at: 2026-10-26. Підстава — заповнені рішення і повідомлення користувача про завершення review.
Перевірити всі вісім полів кожного документа, включно з false/[]; спірні topic labels позначені в поясненнях.

## HR-0743

Джерело: [HR-0743.txt](sourses/hm1/texts/en/HR-0743.txt). Reviewer: автор проєкту; дата: 2026-10-26; статус: approved.

| Поле | Чернетка | Доказ / обґрунтування |
| --- | --- | --- |
| language | `"en"` | 11–98: англійське пояснення |
| primary_topic | `"power_batteries"` | 13,19–23,31–73: оптимізація живлення й заряд |
| mentioned_platforms | `["arduino", "stm32"]` | 13: Arduino Portenta; 77: STM32-based boards |
| mentioned_interfaces | `["wifi", "bluetooth"]` | 71: Wi-Fi, Bluetooth |
| mentions_sensor | `true` | 57,69: sensor network, motion sensors |
| mentions_display | `false` | Немає апаратного дисплея у title/body; RGB LED у 71 не дисплей |
| mentions_battery | `true` | 13,19–53: battery/LiPo |
| mentions_motor | `false` | Немає буквальної згадки мотора у title/body |

Рішення людини / виправлення: затверджую.

## HR-0244

Джерело: [HR-0244.txt](sourses/hm1/texts/uk/HR-0244.txt). Reviewer: автор проєкту; дата: 2026-10-26; статус: approved.

| Поле | Чернетка | Доказ / обґрунтування |
| --- | --- | --- |
| language | `"uk"` | 5–196: українське пояснення |
| primary_topic | `"sensors_measurements"` | 5,62–68: вимірювання залишку філаменту; погоджено автором 26.10.2026 |
| mentioned_platforms | `["esp8266"]` | 30: Wemos D1 mini на основі ESP8266; Arduino не згаданий |
| mentioned_interfaces | `["wifi", "usb"]` | 58,72,88: Wi-Fi; 41,80: Type-C та micro-USB. Обидва роз’єми належать до одного тегу usb; виправлення автора враховано без нового enum |
| mentions_sensor | `true` | 76: тензодатчик; 30: сенсорна кнопка |
| mentions_display | `false` | 30: кільце звичайних LED, не дисплей; веб-інтерфейс не апаратний екран |
| mentions_battery | `false` | В усьому змісті немає батареї/АКБ |
| mentions_motor | `false` | В усьому змісті немає буквального двигуна |

Рішення людини / виправлення: також присутній Type-C роз'єм, після цього виправлення затверджую

## HR-0385

Джерело: [HR-0385.txt](sourses/hm1/texts/en/HR-0385.txt). Reviewer: автор проєкту; дата: 2026-10-26; статус: approved.

| Поле | Чернетка | Доказ / обґрунтування |
| --- | --- | --- |
| language | `"en"` | 11–17: англійське пояснення |
| primary_topic | `"devices_automation"` | 11–15: автоматичний полив; погоджено автором 26.10.2026 |
| mentioned_platforms | `["arduino"]` | 13: Arduino IoT Explorer Kit у змісті, не header |
| mentioned_interfaces | `["wifi"]` | 15: WiFi connectivity |
| mentions_sensor | `true` | 13: soil moisture sensor |
| mentions_display | `false` | 15: Cloud dashboard не апаратний дисплей; інших згадок немає |
| mentions_battery | `true` | 13: 12V battery pack |
| mentions_motor | `false` | 13: pump як відхилена альтернатива; 15: fan, без слова motor/двигун |

Рішення людини / виправлення: затверджую.

## HR-0068

Джерело: [HR-0068.txt](sourses/hm1/texts/ru/HR-0068.txt). Reviewer: автор проєкту; дата: 2026-10-26; статус: approved.

| Поле | Чернетка | Доказ / обґрунтування |
| --- | --- | --- |
| language | `"ru"` | 3–64: російське пояснення |
| primary_topic | `"sensors_measurements"` | 3,18–40: робота датчика нахилу |
| mentioned_platforms | `["arduino"]` | 9,44,54: Arduino UNO |
| mentioned_interfaces | `["usb"]` | 12,54,58: USB |
| mentions_sensor | `true` | 3,26,34,40: датчик нахилу/вібрації |
| mentions_display | `false` | 36,44: звичайні світлодіоди, дисплея немає |
| mentions_battery | `false` | 54: джерело 9В/DC, не явна батарея |
| mentions_motor | `false` | Мотор у title/body не згаданий |

Рішення людини / виправлення: затверджую.

## HR-0254

Джерело: [HR-0254.txt](sourses/hm1/texts/uk/HR-0254.txt). Reviewer: автор проєкту; дата: 2026-10-26; статус: approved.

| Поле | Чернетка | Доказ / обґрунтування |
| --- | --- | --- |
| language | `"uk"` | 3–45: український текст |
| primary_topic | `"displays_indicators"` | 3,41: великі цифри на LCD1602 |
| mentioned_platforms | `["arduino"]` | 9: Arduino Uno; не лише IDE у 33 |
| mentioned_interfaces | `["i2c"]` | 11,17,35,45: I2C |
| mentions_sensor | `false` | Немає сенсора; RTC сам по собі не доводить датчик |
| mentions_display | `true` | 3,11,41: LCD/екран/дисплей |
| mentions_battery | `false` | RTC DS1302 не дозволяє домислити батарею |
| mentions_motor | `false` | Жодної згадки мотора у змісті |

Рішення людини / виправлення: затверджую.

## HR-0212

Джерело: [HR-0212.txt](sourses/hm1/texts/uk/HR-0212.txt). Reviewer: автор проєкту; дата: 2026-10-26; статус: approved.

| Поле | Чернетка | Доказ / обґрунтування |
| --- | --- | --- |
| language | `"uk"` | 3–92: українське пояснення |
| primary_topic | `"power_batteries"` | 3,9–31,80–84: резервне живлення; погоджено автором 26.10.2026 |
| mentioned_platforms | `[]` | 25: узагальнені контролери, жодної enum-платформи |
| mentioned_interfaces | `[]` | У title/body немає семи enum-інтерфейсів |
| mentions_sensor | `true` | 23: датчик іонізації полум’я |
| mentions_display | `false` | 24,71: індикація і звичайні LED, не дисплей |
| mentions_battery | `true` | 9,21–22,30,41,80: автомобільна АКБ |
| mentions_motor | `false` | 3: «двигун прогресу» — метафора, не фізичний двигун |

Рішення людини / виправлення: затверджую.

## HR-0415

Джерело: [HR-0415.txt](sourses/hm1/texts/en/HR-0415.txt). Reviewer: автор проєкту; дата: 2026-10-26; статус: approved.

| Поле | Чернетка | Доказ / обґрунтування |
| --- | --- | --- |
| language | `"en"` | 11–21: англійський текст |
| primary_topic | `"robotics_actuators"` | 11,13,19: шестиколісний робот |
| mentioned_platforms | `["arduino"]` | 11,13,17: Arduino/Mega у змісті |
| mentioned_interfaces | `[]` | 13: PWM не enum; 19: 2.4GHz не дозволяє вивести Wi-Fi |
| mentions_sensor | `false` | Камера у 17 не явний sensor; датчик не названий |
| mentions_display | `false` | Немає апаратного дисплея у змісті |
| mentions_battery | `false` | 19: power supply, не явна battery |
| mentions_motor | `true` | 13,19: six motors |

Рішення людини / виправлення: затверджую.

## HR-0207

Джерело: [HR-0207.txt](sourses/hm1/texts/uk/HR-0207.txt). Reviewer: автор проєкту; дата: 2026-10-26; статус: approved.

| Поле | Чернетка | Доказ / обґрунтування |
| --- | --- | --- |
| language | `"uk"` | 3–36: українське пояснення |
| primary_topic | `"power_batteries"` | 3–21: резервне живлення роутера |
| mentioned_platforms | `[]` | Жодної enum-платформи у title/body |
| mentioned_interfaces | `[]` | Роутер не дозволяє домислити Wi-Fi; протоколів не названо |
| mentions_sensor | `false` | Жодної прямої згадки датчика |
| mentions_display | `false` | Жодного дисплея у змісті |
| mentions_battery | `true` | 7,9: акумулятор lifepo4 |
| mentions_motor | `false` | Реле у 9 не мотор |

Рішення людини / виправлення: затверджую.

## HR-0227

Джерело: [HR-0227.txt](sourses/hm1/texts/uk/HR-0227.txt). Reviewer: автор проєкту; дата: 2026-10-26; статус: approved.

| Поле | Чернетка | Доказ / обґрунтування |
| --- | --- | --- |
| language | `"uk"` | 3–128: українське пояснення |
| primary_topic | `"sensors_measurements"` | 3–7,55,128: обробка вимірювань; погоджено автором 26.10.2026 |
| mentioned_platforms | `["arduino", "raspberry_pi"]` | 23,25: Raspberry Pi Pico; 55,128: Arduino |
| mentioned_interfaces | `[]` | 93: послідовний плотер не доводить UART; інших enum немає |
| mentions_sensor | `true` | 55: датчик атмосферного тиску BMP280 |
| mentions_display | `false` | Графіки/візуалізація у 45,93 не апаратний екран |
| mentions_battery | `false` | Жодної батареї у змісті |
| mentions_motor | `false` | Жодного фізичного мотора у змісті |

Рішення людини / виправлення: затверджую.

## HR-0187

Джерело: [HR-0187.txt](sourses/hm1/texts/uk/HR-0187.txt). Reviewer: автор проєкту; дата: 2026-10-26; статус: approved.

| Поле | Чернетка | Доказ / обґрунтування |
| --- | --- | --- |
| language | `"uk"` | 1–41: українське пояснення |
| primary_topic | `"devices_automation"` | 1,3: автополив рослин |
| mentioned_platforms | `["arduino"]` | 1,3,15,17: Arduino |
| mentioned_interfaces | `[]` | Код digitalRead/digitalWrite не доводить enum-інтерфейсів |
| mentions_sensor | `true` | 3,13,19,27,33: датчик вологості |
| mentions_display | `false` | У змісті й коді немає дисплея |
| mentions_battery | `false` | У змісті й коді немає батареї |
| mentions_motor | `false` | 3,11: помпа; motor у 21–35 лише ім’я змінної, не буквальна згадка двигуна |

Рішення людини / виправлення: затверджую*.
