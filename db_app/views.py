from datetime import datetime
from werkzeug.urls import url_parse
from werkzeug.utils import redirect
from models import *
from flask import Flask, render_template, url_for, request, flash, jsonify
from forms import LoginForm, RegistrationForm, EditFieldForm
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo


# Database.database_creation()

@app.route('/', defaults={'bw': 'Cloud computing'})  # to pre-select a buzz word
@app.route('/<bw>')
def index(bw):
    all_fields = Database.find_all_fields()

    buzzwords = Database.find_buzz_words()[0]['names']

    if bw is not None:
        buzzword_fields = Database.find_buzz_word_fields(bw)
    else:
        buzzword_fields = None

    return render_template('index.html', allFields=all_fields, buzzWords=buzzwords, buzzWordFields=buzzword_fields,
                           word=bw)


@app.route('/home', defaults={'user': ''})
@app.route('/<user>/home')
def home(user):
    classifications_names = Database.find_all_classifications_names()
    return render_template('home.html', classifications_names=classifications_names, title='Home')


# @app.route('/<user>/classifications')
@app.route('/<user>/classifications')  # classification's user only (member'space)
@login_required
def display_classifications_user(user):
    graphs_id = current_user.get_graphs_id()
    classifications_names = Database.find_classifications_names(graphs_id)
    return render_template('home.html', classifications_names=classifications_names,
                           title='My classifications')  # même html ok? mais 'home' pas très expressif


@app.route('/add/classification/')
@login_required
def add_classification():
    return 'ok'


@app.route('/classification/<name>/', defaults={'bw': 'Cloud computing'})
@app.route('/classification/<name>/<bw>')
def display_classification(name, bw):  # id au lieu de name?
    classification = Database.find_classification(name)

    uuid_classification = Database.find_uuid_classification(name)

    buzzwords = Database.find_buzz_words()[0]['names']

    if bw is not None:
        buzzword_fields = Database.find_buzz_word_fields(bw)
    else:
        buzzword_fields = None

    return render_template('classification.html', classification=classification, buzzWords=buzzwords,
                           buzzWordFields=buzzword_fields,
                           word=bw, name=name, uuid_classification=uuid_classification)


@app.route('/questions/<field_name>/')
def display_questions(field_name):
    questions_list = Database.find_questions(field_name)
    subfields = Database.find_subfields(field_name)
    concerned_fields_name = Database.find_concerned_fields(field_name)  # return list of dictionaries
    # example: [{'name' : 'os'}, {}]

    concerned_fields = []  # list of dictionaries --> one dict for each concerned_field
    #  --> key "subfields is a list of subfields
    for field in concerned_fields_name:
        concerned_field = {}
        concerned_field['name'] = field['name']
        uuid = field['uuid']
        print(uuid)
        concerned_field['subfields'] = (Database.find_subfields(field['name']))  # return list of dictionaries
        concerned_fields.append(concerned_field)

    return render_template('questions.html', field=field_name, questionsList=questions_list, subfields=subfields,
                           concernedFields=concerned_fields)


@app.route('/edit_field/<classification_uuid>', methods=['GET', 'POST'])
@login_required
def edit_field(classification_uuid):
    # Si forker --> ajouter rel forked from avant
    uuid_temporaire = "5e6635494d2cd76913ff1850"  # A CHANGER AVEC SUYNCHRO DATA ENTRE MONGODB ET NEO4J
    form = EditFieldForm()

    # print(form.errors)
    root_fields = Database.find_root_fields()
    all_fields = Database.find_all_fieldsss()
    form.root.choices += [(root_field['uuid'], root_field['name']) for root_field in root_fields]
    form.fields.choices += [(field['uuid'], field['name']) for field in all_fields]

    if form.delete.data:
        uuid_field = form.fields.data
        req = Database.delete_field_request(uuid_field)
        timestamp = datetime.utcnow()
        mongo.db.Classification.update_one({'_id': ObjectId(uuid_temporaire)},
                                           {"$push": {'logs': {'timestamp': timestamp, 'request': req}}},
                                           upsert=False)
        return redirect(url_for('home'))  # redirect to la même page? pour autre modification

    if form.edit.data:
        form.new_field.validators = [DataRequired()]
        if form.validate_on_submit():
            uuid_field = form.fields.data
            new_name = form.new_field.data
            req = Database.edit_field_request(uuid_field, new_name)
            timestamp = datetime.utcnow()
            mongo.db.Classification.update_one({'_id': ObjectId(uuid_temporaire)},
                                               {"$push": {'logs': {'timestamp': timestamp, 'request': req}}},
                                               upsert=False)
            # upsert parameter will insert instead of updating if the post is not found in the database.
            return redirect(url_for('home'))  # bonne page?

    return render_template('edit_classification.html', form=form)


@app.route('/get_fields/<id_root>')
def get_fields(id_root):
    fields = Database.find_fields(id_root)
    print(fields)
    if not fields:  # si le dico est vide
        return jsonify([])
    else:
        return jsonify(fields)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():  # Si GET return False
        user = mongo.db.Users.find_one_or_404({"username": form.username.data})
        if user and User.check_password(user['password'], form.password.data):
            user_obj = User(username=user['username'])
            user_obj.set_var(lastname=user['lastname'], firstname=user['firstname'], email=user['email'],
                             job=user['job'], website_url=user['website_url'], graphs_id=user['graphs_id'])
            login_user(user_obj, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)
        else:
            return redirect(url_for('login'))
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user_obj = User(username=form.username.data)
        user_obj.set_var(form.lastname.data, form.firstname.data, form.email.data, form.job.data,
                         form.website_url.data)
        user_obj.set_password(form.password.data)
        user_doc = user_obj.convert_to_doc()
        mongo.db.Users.insert_one(user_doc)
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


if __name__ == "__main__":
    app.secret_key = 'mysecret'  # to change and to securise
    app.run(debug=True)
