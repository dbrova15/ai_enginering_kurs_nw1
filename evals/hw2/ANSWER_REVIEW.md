# Ручна оцінка реальних відповідей ДЗ2

Статус: draft. Жодних людських correct/faithful оцінок агент не заповнював.

Run: `20261117T162104Z-71601edd`

Це відповіді історичного extract-4 run. Після виправлення HTML-коду поточний корпус має інший dataset_id; ці hashes не слід приписувати новому корпусу або автоматично використовувати для його калібрування. Питання/reference цього run збережено в [testset.snapshot.json](runs/20261117T162104Z-71601edd/testset.snapshot.json).


Спочатку незалежно перевірте факти й саме наведені джерела. Машинні verdicts є в run.json; їх не слід переносити в людські labels без перевірки. Hashes і порожній шаблон — у labels.template.json. Для калібрування потрібні ≥10 різних відповідей та обидва класи для correctness і faithfulness.

## hr-q01

Яке живлення потрібне LCD-шилду в статті про термістор та ADC STM32?

LCD-шилд живиться від 3.3V. [Підключення 2.8 TFT LCD Screen модуля до STM32 \(частина 2 - touchscreen\): Підключення 2.8 TFT LCD Screen модуля до STM32 (частина 2 - touchscreen)](https://arduino.ua/art57-pidkluchennya-2-8-tft-lcd-screen-modylya-do-stm32-chastina-2-touchscreen); [Термістор \(терморезистор\). ADC в stm32: Термістор (терморезистор). ADC в stm32](https://arduino.ua/art58-termistor-termorezistor-adc-v-stm32)

LCD-шилд може працювати з живленням від 5V до 3.3V. [Підключення 2.8 TFT LCD Screen модуля до STM32 \(частина 2 - touchscreen\): Підключення 2.8 TFT LCD Screen модуля до STM32 (частина 2 - touchscreen)](https://arduino.ua/art57-pidkluchennya-2-8-tft-lcd-screen-modylya-do-stm32-chastina-2-touchscreen)

Для підсвітки LCD-шилда також можна використовувати 3.3V. [Підключення 2.8 TFT LCD Screen модуля до STM32 \(частина 2 - touchscreen\): Підключення 2.8 TFT LCD Screen модуля до STM32 (частина 2 - touchscreen)](https://arduino.ua/art57-pidkluchennya-2-8-tft-lcd-screen-modylya-do-stm32-chastina-2-touchscreen); [Термістор \(терморезистор\). ADC в stm32: Термістор (терморезистор). ADC в stm32](https://arduino.ua/art58-termistor-termorezistor-adc-v-stm32)

Еталонна чернетка: Живлення та підсвітка LCD шилда 3.3V. Працює по FSMC у 16-бітному режимі.

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q02

Що додає друга частина підключення 2.8 TFT LCD до STM32?

Друга частина підключення 2.8 TFT LCD до STM32 включає підключення резистивної сенсорної панелі на контролері TSC2046 через інтерфейс SPI. [Підключення 2.8 TFT LCD Screen модуля до STM32 \(частина 2 - touchscreen\): Підключення 2.8 TFT LCD Screen модуля до STM32 (частина 2 - touchscreen)](https://arduino.ua/art57-pidkluchennya-2-8-tft-lcd-screen-modylya-do-stm32-chastina-2-touchscreen)

TFT LCD Screen модуль може розпізнавати інформаційні сигнали від 0V до 3.3V як логічні '0' та '1', що важливо для підключення до STM32, де логічна одиниця рівна 3.3V. [Підключення 2.8 TFT LCD Screen модуля до STM32 \(частина 2 - touchscreen\): Підключення 2.8 TFT LCD Screen модуля до STM32 (частина 2 - touchscreen)](https://arduino.ua/art57-pidkluchennya-2-8-tft-lcd-screen-modylya-do-stm32-chastina-2-touchscreen)

Живлення TFT LCD Screen модуля можна змінювати з 5V до 3.3V, підключивши його до ніжки стабілізатора на модулі. [Підключення 2.8 TFT LCD Screen модуля до STM32 \(частина 2 - touchscreen\): Підключення 2.8 TFT LCD Screen модуля до STM32 (частина 2 - touchscreen)](https://arduino.ua/art57-pidkluchennya-2-8-tft-lcd-screen-modylya-do-stm32-chastina-2-touchscreen)

Еталонна чернетка: Дослідивши питання на рахунок живлення контролера дисплея та тачскріна виявилося що цей TFT LCD Screen модуль з легкістю може розпізнавати інформаційні сигнали від 0V до 3.3V як логічні “0” та “1” відповідно (тобто все що більше приблизно 2V він (модуль) сприймає як логічну одиницю). Це дуже важливо при підключенні до stm32 на пряму, адже у цьому контролері логічна одиниця рівна 3.3V. Також живлення теж можна поміняти з 5V до 3.3V, підпаявшись плюсом до однієї з ніжок стабілізатора на модулі (як це показано нижче на малюнку№1 червоною стрілкою). Подавши так само 3.3 V на підсвітку можна повністю відмовитися від 5V.

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q03

Для чого потрібен гістерезис у проєкті термореле з Wi-Fi?

Термореле з гістерезисом використовується для захисту пристроїв від перегріву або переохолодження. [Термореле з гістерезисом та управлінням через Wi-Fi: Термореле з гістерезисом та управлінням через Wi-Fi](https://arduino.ua/art243-termorele-z-gisterezisom-ta-ypravlinnyam-cherez-wi-fi)

Гістерезис дозволяє встановити нижню та верхню межі спрацьовування термореле, що забезпечує контроль за температурою. [Термореле з гістерезисом та управлінням через Wi-Fi: Термореле з гістерезисом та управлінням через Wi-Fi](https://arduino.ua/art243-termorele-z-gisterezisom-ta-ypravlinnyam-cherez-wi-fi)

Термореле може дистанційно керувати потужним навантаженням, таким як електромотор, через Wi-Fi. [Термореле з гістерезисом та управлінням через Wi-Fi: Термореле з гістерезисом та управлінням через Wi-Fi](https://arduino.ua/art243-termorele-z-gisterezisom-ta-ypravlinnyam-cherez-wi-fi)

Пристрій вимикається при досягненні критичних температур, що дозволяє уникнути перегріву електромотора. [Термореле з гістерезисом та управлінням через Wi-Fi: Термореле з гістерезисом та управлінням через Wi-Fi](https://arduino.ua/art243-termorele-z-gisterezisom-ta-ypravlinnyam-cherez-wi-fi)

Гістерезис у термореле дозволяє уникнути частих вмикань і вимикань реле, що може бути викликане незначними коливаннями температури. [Термореле з гістерезисом та управлінням через Wi-Fi: Термореле з гістерезисом та управлінням через Wi-Fi](https://arduino.ua/art243-termorele-z-gisterezisom-ta-ypravlinnyam-cherez-wi-fi)

Еталонна чернетка: Термореле - це прилад, що комутує струм основуючись на температурі навколишнього середовища. Термореле можуть мати гістерезис, різну температуру спрацьовування або її налаштування. Використовують їх зазвичай для захисту пристроїв від перегріву або, в деяких випадках, від переохолодження.

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q04

Як у проєкті моніторингу ваги філаменту використовується Telegram?

Система моніторингу ваги філаменту призначена для вимірювання ваги філаменту, що залишився на котушці, та надсилання інформації через Telegram бот. [Система моніторингу ваги філаменту для 3D принтера через Telegram: Система моніторингу ваги філаменту для 3D принтера через Telegram](https://arduino.ua/art267-sistema-monitoringy-vagi-filamenty-dlya-3d-printera-cherez-telegram)

Система може надсилати сповіщення в Telegram, якщо залишилось мало пластику, наприклад, якщо філаменту на котушці менше 50 г. [Система моніторингу ваги філаменту для 3D принтера через Telegram: Система моніторингу ваги філаменту для 3D принтера через Telegram](https://arduino.ua/art267-sistema-monitoringy-vagi-filamenty-dlya-3d-printera-cherez-telegram)

Пристрій постійно зчитує вагу філаменту і, якщо залишок філаменту падає до порогу (наприклад, 50 г), надсилає команду на базу, яка передає повідомлення у Telegram. [Система моніторингу ваги філаменту для 3D принтера через Telegram: Система моніторингу ваги філаменту для 3D принтера через Telegram](https://arduino.ua/art267-sistema-monitoringy-vagi-filamenty-dlya-3d-printera-cherez-telegram)

Якщо виміряна вага має негативне значення, це вказує на відсутність котушки, і вага тарування скидається, щоб уникнути помилкових повідомлень. [Система моніторингу ваги філаменту для 3D принтера через Telegram: Система моніторингу ваги філаменту для 3D принтера через Telegram](https://arduino.ua/art267-sistema-monitoringy-vagi-filamenty-dlya-3d-printera-cherez-telegram)

При натисканні кнопки на пристрої поточна вага надсилається на базу, а вона, в свою чергу, відправляє повідомлення в Telegram для перевірки філаменту вручну. [Система моніторингу ваги філаменту для 3D принтера через Telegram: Система моніторингу ваги філаменту для 3D принтера через Telegram](https://arduino.ua/art267-sistema-monitoringy-vagi-filamenty-dlya-3d-printera-cherez-telegram)

Для налаштування Telegram бота потрібно створити бота за допомогою @BotFather та скопіювати токен, який потім вставляється в код програми. [Система моніторингу ваги філаменту для 3D принтера через Telegram: Система моніторингу ваги філаменту для 3D принтера через Telegram](https://arduino.ua/art267-sistema-monitoringy-vagi-filamenty-dlya-3d-printera-cherez-telegram)

Користувач повинен отримати ID чату в Telegram, щоб налаштувати систему для надсилання повідомлень. [Система моніторингу ваги філаменту для 3D принтера через Telegram: Система моніторингу ваги філаменту для 3D принтера через Telegram](https://arduino.ua/art267-sistema-monitoringy-vagi-filamenty-dlya-3d-printera-cherez-telegram)

Еталонна чернетка: Розроблена система призначена для вимірювання ваги філаменту що залишився на котушці, та надсиланням інформації через Telegram бот. Система може як просто вимірювати загальну вагу (вага котушки + вага філаменту), так і вимірювати фактичну вагу філаменту (загальна вага - вага котушки = вага філаменту), а також може надсилати сповіщення в Telegram якщо залишилось мало пластику (наприклад якщо філаменту на котушці менше 50г то надсилається сповіщення, і користувач може замінити котушку).

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q05

Яке призначення пристрою для визначення ємності Li-ion акумуляторів?

Прилад для визначення ємності Li-ion акумуляторів допомагає підібрати батареї однакової ємності для використання їх в послідовній зборці. [Прилад для визначення ємності Li-ion акумуляторів: Прилад для визначення ємності Li-ion акумуляторів](https://arduino.ua/art235-prilad-dlya-viznachennya-mnosti-li-ion-akymylyatoriv)

Прилад тестує акумулятори, показуючи значення напруги, струму та часу розряду, а також визначає ємність акумулятора в mA·год. [Прилад для визначення ємності Li-ion акумуляторів: Прилад для визначення ємності Li-ion акумуляторів](https://arduino.ua/art235-prilad-dlya-viznachennya-mnosti-li-ion-akymylyatoriv)

Прилад задовольняє користувача, допомагаючи при складанні акумуляторів у батарею більшої напруги. [Прилад для визначення ємності Li-ion акумуляторів: Прилад для визначення ємності Li-ion акумуляторів](https://arduino.ua/art235-prilad-dlya-viznachennya-mnosti-li-ion-akymylyatoriv)

Еталонна чернетка: Доброго дня. Метою цього проекту було створення пристрою для визначення ємності Li-ion акумуляторів, що допоможе підібрати батареї однакової ємності для використання їх в послідовній зборці.

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q06

Який екран використовується у проєкті годинника на Arduino?

У проєкті годинника на Arduino використовується LCD 1602A з I2C адаптером. [Мій перший крутий годинник на Arduino: як витиснути максимум з екрана 1602: Мій перший крутий годинник на Arduino: як витиснути максимум з екрана 1602](https://arduino.ua/art278-mii-pershii-krytii-godinnik-na-arduino-yak-vitisnyti-maksimym-z-ekrana-1602)

LCD 1602 має два рядки символів. [Мій перший крутий годинник на Arduino: як витиснути максимум з екрана 1602: Мій перший крутий годинник на Arduino: як витиснути максимум з екрана 1602](https://arduino.ua/art278-mii-pershii-krytii-godinnik-na-arduino-yak-vitisnyti-maksimym-z-ekrana-1602)

Еталонна чернетка: Всім привіт! Нещодавно я замовив на arduino.ua кілька модулів і вирішив зібрати щось дійсно корисне для своєї кімнати - настільний годинник. Але стандартні цифри на дисплеї LCD1602 дуже маленькі, і щоб побачити час з іншого кінця кімнати, треба було сильно мружитися. Тому я поставив собі задачу - зробити цифри гігантськими, на всю висоту екрана.

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q07

Що дозволяє роботу визначати лінію у проєкті робота на Arduino?

Робот, який їздить по лінії, оснащується цифровими датчиками лінії, які зчитують показання для визначення лінії. [Створення робота, який їздить по лінії: Створення робота, який їздить по лінії](https://arduino.ua/art185-stvorennya-robota-yakii-izdit-po-linii)

Для побудови робота необхідно використовувати два мікродвигуни з колесами на валах. [Створення робота, який їздить по лінії: Створення робота, який їздить по лінії](https://arduino.ua/art185-stvorennya-robota-yakii-izdit-po-linii)

Для кріплення датчиків потрібно зробити отвори 3мм, щоб вони могли визначити лінію. [Створення робота, який їздить по лінії: Створення робота, який їздить по лінії](https://arduino.ua/art185-stvorennya-robota-yakii-izdit-po-linii)

Еталонна чернетка: При створенні будь-якого робота, потрібно встановити: датчики (показання яких, буде зчитувати робот), керуючі модулі (для виведення результатів роботи) та скетч (це алгоритм за яким повинен працювати робот). У нашому випадку, ми оснащуємо машину, цифровими датчиками лінії, а в ролі керуючих модулів виступатимуть два мікродвигуни з колесами на валах.

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q08

Для чого призначений модуль L293D в описаному проєкті?

L293D являє собою набір із чотирьох драйверів напівмостового типу, які можуть керувати чотирма окремими двигунами постійного струму або двома двигунами з реверсом. [Модуль драйвера двигунів на L293D: Модуль драйвера двигунів на L293D / Третє питання.](https://arduino.ua/art169-modyl-draivera-dvigyniv-na-l293d)

Мостова схема потрібна для того, щоб змінювати напрям струму через двигун при однополярному живленні. [Модуль драйвера двигунів на L293D: Модуль драйвера двигунів на L293D / Третє питання.](https://arduino.ua/art169-modyl-draivera-dvigyniv-na-l293d)

Вихідні каскади мікросхеми L293D мають вбудовані діоди для захисту від ЕРС самоіндукції при індуктивному навантаженні. [Модуль драйвера двигунів на L293D: Модуль драйвера двигунів на L293D / Третє питання.](https://arduino.ua/art169-modyl-draivera-dvigyniv-na-l293d)

Плата драйвера двигунів живиться від напруги VIN = 9–24 В, яка повинна бути на 2,5…3 В більшою від номінальної напруги двигуна. [Модуль драйвера двигунів на L293D: Модуль драйвера двигунів на L293D / Третє питання.](https://arduino.ua/art169-modyl-draivera-dvigyniv-na-l293d)

Еталонна чернетка: Сьогодні в центрі уваги опинився простий і водночас загадковий пристрій « Модуль драйвера двигунів на L293D ».

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q09

Яке призначення BMS у статті про підключення Li-ion акумуляторів?

BMS (Battery Management System) використовується для підключення акумуляторної збірки до системи, що забезпечує контроль за зарядом та розрядом акумуляторів. [Підключення LI-ion акумуляторів до BMS: Підключення LI-ion акумуляторів до BMS](https://arduino.ua/art251-pidkluchennya-li-ion-akymylyatoriv-do-bms); [Підключення LI-ion акумуляторів до BMS: Підключення LI-ion акумуляторів до BMS](https://arduino.ua/art251-pidkluchennya-li-ion-akymylyatoriv-do-bms)

BMS підбирається за характеристиками під високострумові акумулятори, щоб уникнути перегріву та переходу в захист. [Підключення LI-ion акумуляторів до BMS: Підключення LI-ion акумуляторів до BMS](https://arduino.ua/art251-pidkluchennya-li-ion-akymylyatoriv-do-bms)

Після підключення акумулятора до BMS, його можна використовувати в різних саморобках та пристроях. [Підключення LI-ion акумуляторів до BMS: Підключення LI-ion акумуляторів до BMS](https://arduino.ua/art251-pidkluchennya-li-ion-akymylyatoriv-do-bms)

Еталонна чернетка: 2. Плату BMS підбираємо за характеристиками під високоcтрумові акумулятори, щоб BMS не переходила в захист і не перегрівалася.

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q10

Як у статті пропонується програмувати ESP32 мовою Python?

Програмування ESP32 на Python - це зручний спосіб розробки для початківців та потужний інструмент для професіоналів. [Чи можна програмувати esp 32 на Python?: Чи можна програмувати esp 32 на Python?](https://arduino.ua/art239-chi-mojna-programyvati-esp-32-na-python)

Zerynth Studio - це потужний інструмент для розробки вбудованих додатків на мові Python для платформи ESP32. [Чи можна програмувати esp 32 на Python?: Чи можна програмувати esp 32 на Python?](https://arduino.ua/art239-chi-mojna-programyvati-esp-32-na-python)

MicroPython - це реалізація мови Python3, спеціально призначена для мікроконтролерів. [Чи можна програмувати esp 32 на Python?: Чи можна програмувати esp 32 на Python?](https://arduino.ua/art239-chi-mojna-programyvati-esp-32-na-python); [Чи можна програмувати esp 32 на Python?: Чи можна програмувати esp 32 на Python?](https://arduino.ua/art239-chi-mojna-programyvati-esp-32-na-python)

MicroPython надає зручний спосіб програмування мікроконтролера. Ви можете використовувати звичайний Python-синтаксис для розробки програм. [Чи можна програмувати esp 32 на Python?: Чи можна програмувати esp 32 на Python?](https://arduino.ua/art239-chi-mojna-programyvati-esp-32-na-python)

Ви можете взаємодіяти з ESP32 через REPL (Read-Eval-Print Loop), що дозволяє вам виконувати команди без необхідності завантажувати код на контролер. [Чи можна програмувати esp 32 на Python?: Чи можна програмувати esp 32 на Python?](https://arduino.ua/art239-chi-mojna-programyvati-esp-32-na-python)

З MicroPython ви зможете програмувати ESP32, використовуючи звичайний Python. Наприклад, ви можете контролювати GPIO, взаємодіяти з мережею та робити багато інших речей. [Чи можна програмувати esp 32 на Python?: Чи можна програмувати esp 32 на Python?](https://arduino.ua/art239-chi-mojna-programyvati-esp-32-na-python)

Еталонна чернетка: ESP32 - це мікроконтролер з підтримкою бездротових інтерфейсів Wi-Fi та Bluetooth, який може використовуватися для створення різноманітних пристроїв Інтернету речей (IoT) з використанням мови програмування Python.

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q11

Какова задача робота в соревновании mini Sumo?

У соревновании mini Sumo роботи встановлюються на полі, напроти один одного, і їхня задача полягає в тому, щоб самостійно витолкнути супротивника за межі поля. [Робот Sumo на Arduino Nano: Робот Sumo на Arduino Nano](https://arduino.ua/art1-robot-sumo-na-arduino-nano)

Робот має програму, алгоритм якої дозволяє використовувати хитрість або силу для досягнення мети. [Робот Sumo на Arduino Nano: Робот Sumo на Arduino Nano](https://arduino.ua/art1-robot-sumo-na-arduino-nano)

Коли один з роботів витолкнув супротивника за поле, цей робот стає переможцем. [Робот Sumo на Arduino Nano: Робот Sumo на Arduino Nano](https://arduino.ua/art1-robot-sumo-na-arduino-nano)

Робот використовує фотосенсори для виявлення супротивника і коригує свою траєкторію руху в залежності від даних з сенсорів. [Робот Sumo на Arduino Nano: Робот Sumo на Arduino Nano](https://arduino.ua/art1-robot-sumo-na-arduino-nano)

Концепція робота Sumoard полягає в його треугольній формі, що дозволяє на великій швидкості підцепити супротивника і зробити його неуправляємим. [Робот Sumo на Arduino Nano: Робот Sumo на Arduino Nano](https://arduino.ua/art1-robot-sumo-na-arduino-nano)

Еталонна чернетка: Сборка робота - это увлекательное занятие, особенно если робот будет принимать участие в соревнованиях. Конечно, спортивное состязание mini Sumo привлечет много зрителей и любителей микроконтроллерной техники. В соревновании mini Sumo роботы устанавливаются на поле, напротив друг друга. Задача роботов, самостоятельно вытолкнуть соперника за пределы поля. Что бы это сделать, робот имеет программу, алгоритм которой позволяет прибегнуть к хитрости, или к силе. Но собрать робота из электронных деталей не всегда возможно. И времени на конструирование мало и знаний недостаточно. В продаже появились платы для конструирования микроконтроллерных систем. Такие платы помогают быстро собрать конструкцию. Одна из них Arduino Nano. Полное описание платы микроконтроллера можно получить на arduino.cc . [1]

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q12

Что обнаруживает модуль SW-520D?

Модуль SW-520D является датчиком наклона, который определяет, наклонен ли объект или нет. [Модуль датчика наклона и вибрации SW-520D: Модуль датчика наклона и вибрации SW-520D](https://arduino.ua/art72-modyl-datchika-naklona-i-vibracii-sw-520d)

SW-520D использует технологию роликового типа, состоящую из двух проводящих элементов и проводящей свободной массы, которая при наклоне замыкает контакты, действуя как переключатель. [Модуль датчика наклона и вибрации SW-520D: Модуль датчика наклона и вибрации SW-520D](https://arduino.ua/art72-modyl-datchika-naklona-i-vibracii-sw-520d)

Модуль SW-520D может выдавать логический уровень LOW, когда датчик наклонен ниже порогового угла, и HIGH, когда наклонен выше порогового угла, который составляет от 45 до 130 градусов. [Модуль датчика наклона и вибрации SW-520D: Модуль датчика наклона и вибрации SW-520D](https://arduino.ua/art72-modyl-datchika-naklona-i-vibracii-sw-520d)

SW-520D также может использоваться в качестве датчика вибрации. [Модуль датчика наклона и вибрации SW-520D: Модуль датчика наклона и вибрации SW-520D](https://arduino.ua/art72-modyl-datchika-naklona-i-vibracii-sw-520d)

Еталонна чернетка: Модуль датчика наклона оснащен датчиком наклона и потенциометром. Вы можете прикрепить его к любому объекту, и он определит, наклонен ли объект или нет. На этом уроке мы узнаем, как работает сенсорный модуль наклона и как его использовать с Arduino Board для определения угла наклона или движения.

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q13

How much ROM is specified for the ESP32 series?

ESP32 contains 448 KB of ROM for booting and core functions. [ESP32 technical documentation: Сторінка 26; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf#page=26); [ESP32 technical documentation: Сторінка 4; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf#page=4)

ESP32-S3 contains 384 KB of ROM for booting and core functions. [ESP32-S3 technical documentation: Сторінка 38; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf#page=38)

Еталонна чернетка: • 448 KB ROM

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q14

Which CPU core architecture is specified for ESP32-S3?

ESP32-S3 has a low-power Xtensa® dual-core 32-bit LX7 microprocessor. [ESP32-S3 technical documentation: Сторінка 36; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf#page=36)

ESP32-S3 features a five-stage pipeline that supports the clock frequency of up to 240 MHz. [ESP32-S3 technical documentation: Сторінка 36; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf#page=36)

Еталонна чернетка: Xtensa® 32-bit LX7 dual-core microprocessor

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q15

Які обсяги Flash наведені для medium-density STM32F103x8/xB?

STM32F103x8 і STM32F103xB мають 64 або 128 КБ Flash пам'яті. [STM32F103C8 technical documentation: Сторінка 1; розділ не визначено](https://www.st.com/resource/en/datasheet/stm32f103c8.pdf#page=1)

STM32F103x8 і STM32F103xB відносяться до середньої щільності (medium-density) пристроїв. [STM32F103C8 technical documentation: Сторінка 13; розділ не визначено](https://www.st.com/resource/en/datasheet/stm32f103c8.pdf#page=13)

Еталонна чернетка: 64 or 128 KB Flash, USB, CAN, 7 timers, 2 ADCs, 9 com. interfaces

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q16

Які обсяги Flash наведені для high-density STM32F103xC/xD/xE?

STM32F103xC, STM32F103xD, STM32F103xE мають Flash пам'ять від 256 до 512 Кбайт. [STM32F103VD technical documentation: Сторінка 1; розділ не визначено](https://www.st.com/resource/en/datasheet/stm32f103vd.pdf#page=1); [STM32F103VD technical documentation: Сторінка 10; розділ не визначено](https://www.st.com/resource/en/datasheet/stm32f103vd.pdf#page=10)

STM32F103xC, STM32F103xD, STM32F103xE є пристроями високої щільності. [STM32F103VD technical documentation: Сторінка 14; розділ не визначено](https://www.st.com/resource/en/datasheet/stm32f103vd.pdf#page=14); [STM32F103C8 technical documentation: Сторінка 13; розділ не визначено](https://www.st.com/resource/en/datasheet/stm32f103c8.pdf#page=13)

Еталонна чернетка: – 256 to 512 Kbytes of Flash memory

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q17

Яка версія саме наданого datasheet ESP32: 4.9 чи 5.3? Не роби висновку про всі зовнішні джерела.

Версія наданого datasheet ESP32 є 5.3. [ESP32 technical documentation: Сторінка 1; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf#page=1); [ESP32 technical documentation: Сторінка 7; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf#page=7); [ESP32 technical documentation: Сторінка 77; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf#page=77); [ESP32 technical documentation: Сторінка 24; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf#page=24); [ESP32 technical documentation: Сторінка 67; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf#page=67)

Еталонна чернетка: Version 5.3

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q18

Чи правильно називати наданий datasheet ESP32-S3 версією 1.0, чи в ньому зазначено 2.2?

ESP32-S3 Series Datasheet зазначає версію 2.2. [ESP32-S3 technical documentation: Сторінка 1; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf#page=1)

ESP32-S3 Series Datasheet на сторінці 64 також вказує версію v2.2. [ESP32-S3 technical documentation: Сторінка 64; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf#page=64)

ESP32-S3 Series Datasheet на сторінці 21 вказує версію v2.2. [ESP32-S3 technical documentation: Сторінка 21; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf#page=21)

ESP32-S3 Series Datasheet на сторінці 47 зазначає версію v2.2. [ESP32-S3 technical documentation: Сторінка 47; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf#page=47)

ESP32-S3 Series Datasheet на сторінці 45 також вказує версію v2.2. [ESP32-S3 technical documentation: Сторінка 45; розділ не визначено](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf#page=45)

Еталонна чернетка: Version 2.2

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q19

Яка офіційна кількість GPIO у вигаданого контролера HR-Z9999?

У документах недостатньо даних для відповіді.

Еталонна чернетка: Очікується not_found; відсутність доказу має перевірити людина.

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

## hr-q20

Яку гарантійну вартість доставки HR-Z9999 до Антарктиди встановлює цей корпус?

У документах недостатньо даних для відповіді.

Еталонна чернетка: Очікується not_found; відсутність доказу має перевірити людина.

Фактичний контекст: [run.json](runs/20261117T162104Z-71601edd/run.json), поле records для цього case.

- Correct: не оцінено людиною.
- Faithful: не оцінено людиною.
- Пояснення: заповнює людина.

