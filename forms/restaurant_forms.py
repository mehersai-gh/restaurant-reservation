from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms import StringField, IntegerField, FileField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class RestaurantForm(FlaskForm):
    name = StringField('Restaurant Name', validators=[DataRequired()])
    four_table = IntegerField('Number of 4-Seater Tables', validators=[DataRequired(), NumberRange(min=0)])
    two_table = IntegerField('Number of 2-Seater Tables', validators=[DataRequired(), NumberRange(min=0)])
    photo = FileField('Restaurant Photo', validators=[DataRequired()])
    submit = SubmitField('Add Restaurant')
