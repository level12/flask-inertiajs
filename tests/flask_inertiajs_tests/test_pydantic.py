from unittest.mock import Mock

from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from flask_inertiajs.pydantic import validate, validation_errors

from .helpers import TenForwardForm


class TestValidationErrors:
    def test_errors(self):
        error = ValidationError.from_exception_data(
            'Red alert!',
            [
                {
                    'loc': ('captainName',),
                    'type': PydanticCustomError('missing_captain', 'Identify yourself, captain.'),
                    'input': {},
                },
                {
                    'loc': ('captainName',),
                    'type': PydanticCustomError('unavailable_captain', 'Picard is on shore leave.'),
                    'input': 'Picard',
                },
                {
                    'loc': ('crew', 0, 'dutyStation'),
                    'type': PydanticCustomError('unassigned', 'Report to engineering.'),
                    'input': {},
                },
                {
                    'loc': (),
                    'type': PydanticCustomError('red_alert', 'All hands to battle stations.'),
                    'input': {'captainName': 'Picard'},
                },
            ],
        )

        assert validation_errors(error) == {
            'captainName': 'Picard is on shore leave.',  # Last message for a field wins.
            'crew.0.dutyStation': 'Report to engineering.',
            '': 'All hands to battle stations.',
        }


class TestValidate:
    def test_success_and_context(self):
        result, errors = validate(
            TenForwardForm,
            {'bartenderName': ' Guinan '},
            context={'bartenders': ['Guinan']},
        )

        assert isinstance(result, TenForwardForm)
        assert result.bartender_name == 'Guinan'
        assert result.customer_count == 1
        assert errors == {}

    def test_invalid(self):
        result, errors = validate(
            TenForwardForm,
            {'bartenderName': 'Rom'},
            context={'bartenders': ['Guinan']},
        )

        assert result is None
        assert errors == {'bartenderName': 'Value error, Not a bartender'}

    def test_translation(self):
        translator = Mock(return_value='Identify yourself, bartender.')
        on_untranslated = Mock()

        result, errors = validate(
            TenForwardForm,
            {'bartenderName': '', 'customerCount': 'Wesley'},
            context={'bartenders': ['Guinan']},
            translations={'string_too_short': translator},
            on_untranslated=on_untranslated,
        )
        assert result is None
        assert errors == {
            # "Translates" error message according to `translations`
            'bartenderName': 'Identify yourself, bartender.',
            # Falls back to english
            'customerCount': (
                'Input should be a valid integer, unable to parse string as an integer'
            ),
        }
        translator.assert_called_once_with({'min_length': 1})
        on_untranslated.assert_called_once_with('int_parsing')
