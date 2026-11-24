"""Консервативний облік per-run витрат до кожної transport-спроби."""

from decimal import Decimal


class Budget:
    """Резервує верхню оцінку ціни до запиту й уточнює її за usage.

    Decimal запобігає накопиченню похибок float. Невідомий usage не
    звільняє резерв; це не гарантує загального бюджету всіх CI-запусків,
    тому provider-side контроль лишається окремою вимогою.
    """
    def __init__(self, limit: float, input_rate: float, output_rate: float):
        """Приймає погоджений USD cap і тарифи за мільйон токенів.

        Негативні/нескінченні значення відхиляються. spent включає
        реальний usage або консервативну оцінку невідомої спроби.
        """
        self.limit = Decimal(str(limit))
        self.input_rate, self.output_rate = Decimal(str(input_rate)), Decimal(str(output_rate))
        if not self.limit.is_finite() or self.limit <= 0 or any(not v.is_finite() or v < 0 for v in (self.input_rate, self.output_rate)):
            raise ValueError("Некоректні ліміт або тарифи бюджету")
        self.spent = Decimal(0)
        self.unknown_calls = 0

    def price(self, input_tokens: int, output_tokens: int) -> Decimal:
        """Повертає USD без округлення для відомої кількості токенів.

        Від'ємні значення не приймаються. Формула однакова для generator
        і judge, а окремі призначення фіксує журнал кожного виклику.
        """
        if min(input_tokens, output_tokens) < 0:
            raise ValueError("Usage не може бути від'ємним")
        return (input_tokens * self.input_rate + output_tokens * self.output_rate) / Decimal(1_000_000)

    def reserve(self, max_input: int, max_output: int) -> Decimal:
        """Перевіряє й одразу дебетує worst-case резерв до мережі.

        Якщо cap не вистачає навіть для однієї повної спроби, API не
        викликається. Повертає reservation для подальшого settle.
        """
        amount = self.price(max_input, max_output)
        if self.spent + amount > self.limit:
            raise ValueError("budget_exhausted: виклик не виконано")
        self.spent += amount
        return amount

    def settle(self, reserved: Decimal, input_tokens: int | None, output_tokens: int | None) -> None:
        """Уточнює резерв за usage; невідомі значення лишають worst case.

        Перевищення очікуваного model cap є помилкою профілю та блокує
        подальші виклики. Нульові зовнішні тарифи не означають нульових
        витрат на локальне обладнання.
        """
        if input_tokens is None or output_tokens is None:
            self.unknown_calls += 1
            return
        actual = self.price(input_tokens, output_tokens)
        self.spent += actual - reserved
        if actual > reserved or self.spent > self.limit:
            raise ValueError("budget_profile_mismatch: фактичний usage перевищив резерв")
