"""BUG-37 — spoken numbers: the Russian decimal reading and numeral-unit agreement.

`decimal_to_text_ru` was a money formatter pressed into general service: called without
units (the TTS path) it quantized to 2 places and read the remainder as a bare integer —
24.5 → «двадцать четыре пятьдесят», 24.125 → «двадцать четыре двенадцать». Its own
docstring promised «целых … сотых»; now implemented. `plural_form` backs the template-side
unit declension («один градус / двадцать четыре градуса / пять градусов»).
"""

from locveil_voice.utils.text_processing import (
    all_num_to_text,
    decimal_to_text_ru,
    plural_form,
)


class TestDecimalReading:
    def test_half_degree(self):
        assert decimal_to_text_ru("24.5") == "двадцать четыре целых пять десятых"

    def test_hundredths_docstring_promise(self):
        assert decimal_to_text_ru("12.34") == "двенадцать целых тридцать четыре сотых"

    def test_thousandths(self):
        assert decimal_to_text_ru("24.125") == "двадцать четыре целых сто двадцать пять тысячных"

    def test_deeper_than_speech_goes_quantizes_to_thousandths(self):
        assert decimal_to_text_ru("1.23456") == "одна целая двести тридцать пять тысячных"

    def test_integral_float_has_no_fraction(self):
        assert decimal_to_text_ru("22.0") == "двадцать два"

    def test_trailing_zeros_reduce_the_denominator(self):
        assert decimal_to_text_ru("24.50") == "двадцать четыре целых пять десятых"

    def test_zero_integral(self):
        assert decimal_to_text_ru("0.5") == "ноль целых пять десятых"

    def test_negative(self):
        assert decimal_to_text_ru("-10.5") == "минус десять целых пять десятых"

    def test_feminine_agreement_on_one_and_two(self):
        assert decimal_to_text_ru("2.1") == "две целых одна десятая"
        assert decimal_to_text_ru("21.2") == "двадцать одна целая две десятых"

    def test_money_path_unchanged(self):
        assert decimal_to_text_ru(
            "12.34",
            int_units=(('рубль', 'рубля', 'рублей'), 'm'),
            exp_units=(('копейка', 'копейки', 'копеек'), 'f'),
        ) == "двенадцать рублей тридцать четыре копейки"


class TestAllNumToTextIntegration:
    def test_decimal_in_sentence(self):
        assert all_num_to_text("Сейчас 24.5 градуса", "ru") \
            == "Сейчас двадцать четыре целых пять десятых градуса"

    def test_docstring_example(self):
        assert all_num_to_text("У меня 5 яблок и 2.5 кг груш") \
            == "У меня пять яблок и две целых пять десятых кг груш"


class TestPluralForm:
    DEGREES = ["градус", "градуса", "градусов"]

    def test_ru_three_forms(self):
        assert plural_form(1, self.DEGREES) == "градус"
        assert plural_form(21, self.DEGREES) == "градус"
        assert plural_form(2, self.DEGREES) == "градуса"
        assert plural_form(24, self.DEGREES) == "градуса"
        assert plural_form(5, self.DEGREES) == "градусов"
        assert plural_form(0, self.DEGREES) == "градусов"
        # the 11–14 exception
        assert plural_form(11, self.DEGREES) == "градусов"
        assert plural_form(12, self.DEGREES) == "градусов"
        assert plural_form(111, self.DEGREES) == "градусов"

    def test_non_integral_takes_many(self):
        assert plural_form(24.5, self.DEGREES) == "градусов"

    def test_en_singular_plural(self):
        assert plural_form(1, ["degree", "degrees"], "en") == "degree"
        assert plural_form(24, ["degree", "degrees"], "en") == "degrees"

    def test_single_form_is_invariant(self):
        assert plural_form(1, ["percent"], "en") == "percent"
        assert plural_form(42, ["percent"], "en") == "percent"
