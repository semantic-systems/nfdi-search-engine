from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, widgets
from wtforms.validators import (
    ValidationError,
    DataRequired,
    Email,
    EqualTo,
    StopValidation,
)
from wtforms.fields import SelectMultipleField


class ProfileForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    email = StringField(
        "Email",
        render_kw={"disabled": "disabled"},
    )
    submit = SubmitField("Save")


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(html_tag="ol", prefix_label=False)
    option_widget = widgets.CheckboxInput()


class MultiCheckboxAtLeastOne:
    def __init__(self, message=None):
        if not message:
            message = "At least one option must be selected."
        self.message = message

    def __call__(self, form, field):
        if len(field.data) == 0:
            raise StopValidation(self.message)


class PreferencesForm(FlaskForm):
    data_sources = MultiCheckboxField(
        "Data Sources", validators=[MultiCheckboxAtLeastOne()], coerce=str
    )
    submit = SubmitField("Save")
