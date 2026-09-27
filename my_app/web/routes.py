import os
from datetime import datetime

from flask import Blueprint, Response, abort, current_app, jsonify, flash, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload

from my_app.extensions import db
from my_app.forms import MaterialForm, CoatingForm, MillingGeometryForm, TurningGeometryForm, DrillGeometryForm, \
    ConfirmImportForm, DeleteConfirmationForm, ExperimentForm, ImportUploadForm, InsertForm, LoginForm, TapForm, ToolForm, UserForm
from my_app.models import Material, Tool, Coating, Experiment, RecommendationParameter, Adhesive, Coefficient, \
    ImportBatch, MaterialType, MillingGeometry, WearMeasurement, DrillGeometry, TurningGeometry, Insert, TapGeometry, User
from my_app.security import roles_required
from my_app.services.calculations import calculate_cutting_parameters
from my_app.services.cutting_calculations import (
    CalculationInputError,
    calculate_milling,
    calculate_threading,
    calculate_turning,
)
from my_app.services.cutting_reference import get_cutting_reference
from my_app.services.experiment_import import ImportFileError, csv_template, issues_summary, save_uploaded_import_files, validate_import_files
from my_app.services.processing import (
    FUTURE_PROCESSING_TYPES,
    PROCESSING_TYPES,
    get_processing,
    is_available_processing,
)

web_bp = Blueprint('web', __name__)


@web_bp.app_context_processor
def inject_delete_confirmation_form():
    """Делает CSRF-токен доступным для единого модального окна удаления."""
    return {'delete_form': DeleteConfirmationForm()}


@web_bp.before_request
def require_authenticated_user():
    if not current_app.config.get('AUTH_REQUIRED', True):
        return None
    if request.endpoint in {'web.login', 'static'} or current_user.is_authenticated:
        return None
    return redirect(url_for('web.login', next=request.url))


@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('web.select_parameters'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.username == form.username.data))
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(request.args.get('next') or url_for('web.select_parameters'))
        flash('Неверный логин или пароль.', 'danger')
    return render_template('login.html', form=form)


@web_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('web.login'))


@web_bp.route('/users', methods=['GET', 'POST'])
@roles_required('admin')
def users():
    form = UserForm()
    if form.validate_on_submit():
        if db.session.scalar(db.select(User).where(User.username == form.username.data)):
            flash('Такой логин уже существует.', 'danger')
        else:
            user = User(username=form.username.data, role=form.role.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Пользователь создан.', 'success')
            return redirect(url_for('web.users'))
    return render_template(
        'users.html',
        form=form,
        users=db.session.scalars(db.select(User).order_by(User.username)).all(),
    )


@web_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@roles_required('admin')
def delete_user(user_id):
    """Удаляет выбранную учётную запись после подтверждения администратора."""
    form = DeleteConfirmationForm()
    if not form.validate_on_submit():
        flash('Не удалось подтвердить удаление пользователя.', 'danger')
        return redirect(url_for('web.users'))

    user = db.get_or_404(User, user_id)
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'Пользователь «{username}» удалён.', 'success')
    return redirect(url_for('web.users'))


def _get_import_batch_for_current_user(import_batch_id):
    import_batch = db.get_or_404(ImportBatch, import_batch_id)
    if current_user.role != 'admin' and import_batch.uploader_id != current_user.id:
        abort(403)
    return import_batch


def _record_preview_result(import_batch, preview):
    import_batch.experiment_rows = preview.experiment_rows
    import_batch.wear_rows = preview.wear_rows
    import_batch.error_count = preview.error_count
    import_batch.errors_summary = issues_summary(preview)
    import_batch.status = 'preview' if preview.is_valid else 'invalid'
    if preview.is_valid and import_batch.review_status == 'published':
        import_batch.review_status = 'pending'


@web_bp.route('/imports')
@roles_required('admin', 'writer')
def imports():
    statement = db.select(ImportBatch).order_by(ImportBatch.created_at.desc())
    if current_user.role != 'admin':
        statement = statement.where(ImportBatch.uploader_id == current_user.id)
    return render_template('imports.html', import_batches=db.session.scalars(statement).all())


@web_bp.route('/imports/upload', methods=['GET', 'POST'])
@roles_required('admin', 'writer')
def upload_import():
    form = ImportUploadForm()
    if form.validate_on_submit():
        try:
            experiments_path, wear_path, checksum = save_uploaded_import_files(
                form.experiments_file.data,
                form.wear_file.data,
                current_app.config['IMPORT_UPLOAD_FOLDER'],
                current_app.config['IMPORT_MAX_FILE_SIZE'],
            )
            preview = validate_import_files(experiments_path, wear_path)
        except ImportFileError as error:
            flash(str(error), 'danger')
        else:
            import_batch = ImportBatch(
                uploader_id=current_user.id,
                experiments_filename=secure_filename(form.experiments_file.data.filename) or 'experiments.csv',
                wear_filename=(secure_filename(form.wear_file.data.filename) or 'wear_measurements.csv') if form.wear_file.data else None,
                experiments_path=experiments_path,
                wear_path=wear_path,
                checksum=checksum,
            )
            _record_preview_result(import_batch, preview)
            db.session.add(import_batch)
            db.session.commit()
            return redirect(url_for('web.import_preview', import_batch_id=import_batch.id))
    return render_template('import_upload.html', form=form)


@web_bp.route('/imports/<int:import_batch_id>')
@roles_required('admin', 'writer')
def import_preview(import_batch_id):
    import_batch = _get_import_batch_for_current_user(import_batch_id)
    return render_template(
        'import_preview.html',
        import_batch=import_batch,
        issues=(import_batch.errors_summary or '').splitlines(),
        confirm_form=ConfirmImportForm(),
        can_publish=current_user.role == 'admin',
    )


@web_bp.route('/imports/<int:import_batch_id>/confirm', methods=['POST'])
@roles_required('admin', 'writer')
def confirm_import(import_batch_id):
    import_batch = _get_import_batch_for_current_user(import_batch_id)
    form = ConfirmImportForm()
    if not form.validate_on_submit():
        flash('Не удалось подтвердить импорт.', 'danger')
        return redirect(url_for('web.import_preview', import_batch_id=import_batch.id))
    if import_batch.status != 'preview':
        flash('Подтвердить можно только импорт без ошибок, ожидающий подтверждения.', 'warning')
        return redirect(url_for('web.import_preview', import_batch_id=import_batch.id))

    try:
        preview = validate_import_files(import_batch.experiments_path, import_batch.wear_path)
    except ImportFileError as error:
        import_batch.status = 'failed'
        import_batch.error_count = 1
        import_batch.errors_summary = str(error)
        db.session.commit()
        flash('Не удалось повторно прочитать файлы импорта.', 'danger')
        return redirect(url_for('web.import_preview', import_batch_id=import_batch.id))

    if not preview.is_valid:
        _record_preview_result(import_batch, preview)
        db.session.commit()
        flash('Данные изменились или перестали соответствовать справочникам. Импорт не выполнен.', 'danger')
        return redirect(url_for('web.import_preview', import_batch_id=import_batch.id))

    try:
        experiments_by_external_id = {}
        publication_status = 'published' if current_user.role == 'admin' else 'draft'
        for values in preview.experiments:
            external_id = values.pop('external_id')
            experiment = Experiment(
                external_id=external_id,
                import_batch=import_batch,
                publication_status=publication_status,
                **values,
            )
            db.session.add(experiment)
            experiments_by_external_id[external_id] = experiment
        db.session.flush()
        for values in preview.wear_measurements:
            experiment = experiments_by_external_id[values['external_id']]
            db.session.add(WearMeasurement(experiment_id=experiment.id, length=values['length'], wear=values['wear']))

        import_batch.status = 'completed'
        import_batch.review_status = 'published' if current_user.role == 'admin' else 'pending'
        if current_user.role == 'admin':
            import_batch.reviewed_by_id = current_user.id
            import_batch.reviewed_at = datetime.utcnow()
        import_batch.imported_experiments = len(preview.experiments)
        import_batch.imported_wear = len(preview.wear_measurements)
        import_batch.error_count = 0
        import_batch.errors_summary = None
        import_batch.completed_at = datetime.utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()
        failed_batch = db.session.get(ImportBatch, import_batch_id)
        failed_batch.status = 'failed'
        failed_batch.error_count = 1
        failed_batch.errors_summary = 'Ошибка базы данных: импорт отменён целиком, записи не добавлены.'
        db.session.commit()
        flash('Импорт отменён: ни одна запись не была добавлена.', 'danger')
        return redirect(url_for('web.import_preview', import_batch_id=import_batch_id))

    flash(f'Импорт завершён: экспериментов — {import_batch.imported_experiments}, точек износа — {import_batch.imported_wear}.', 'success')
    if current_user.role != 'admin':
        flash('Импорт отправлен администратору на проверку. До публикации он не виден читателям.', 'info')
    return redirect(url_for('web.import_preview', import_batch_id=import_batch.id))


@web_bp.route('/imports/<int:import_batch_id>/publish', methods=['POST'])
@roles_required('admin')
def publish_import(import_batch_id):
    """Публикует импорт после проверки администратором."""

    import_batch = db.get_or_404(ImportBatch, import_batch_id)
    if import_batch.status != 'completed' or import_batch.review_status not in {'pending', 'rejected'}:
        flash('Опубликовать можно только завершённый импорт, ожидающий проверки.', 'warning')
        return redirect(url_for('web.import_preview', import_batch_id=import_batch.id))
    for experiment in import_batch.experiments:
        experiment.publication_status = 'published'
    import_batch.review_status = 'published'
    import_batch.reviewed_by_id = current_user.id
    import_batch.reviewed_at = datetime.utcnow()
    import_batch.review_comment = None
    db.session.commit()
    flash('Импорт опубликован. Эксперименты доступны читателям.', 'success')
    return redirect(url_for('web.import_preview', import_batch_id=import_batch.id))


@web_bp.route('/imports/<int:import_batch_id>/reject', methods=['POST'])
@roles_required('admin')
def reject_import(import_batch_id):
    """Скрывает импорт и оставляет его в журнале с причиной отказа."""

    import_batch = db.get_or_404(ImportBatch, import_batch_id)
    if import_batch.status != 'completed' or import_batch.review_status != 'pending':
        flash('Отклонить можно только импорт, ожидающий проверки.', 'warning')
        return redirect(url_for('web.import_preview', import_batch_id=import_batch.id))
    import_batch.review_status = 'rejected'
    import_batch.reviewed_by_id = current_user.id
    import_batch.reviewed_at = datetime.utcnow()
    import_batch.review_comment = (request.form.get('review_comment') or '').strip()[:2000] or None
    for experiment in import_batch.experiments:
        experiment.publication_status = 'rejected'
    db.session.commit()
    flash('Импорт отклонён и скрыт от читателей.', 'warning')
    return redirect(url_for('web.import_preview', import_batch_id=import_batch.id))


@web_bp.route('/imports/<int:import_batch_id>/files/<string:file_kind>')
@roles_required('admin', 'writer')
def download_import_file(import_batch_id, file_kind):
    import_batch = _get_import_batch_for_current_user(import_batch_id)
    files = {
        'experiments': (import_batch.experiments_path, import_batch.experiments_filename),
        'wear': (import_batch.wear_path, import_batch.wear_filename),
    }
    if file_kind not in files:
        abort(404)
    path, filename = files[file_kind]
    if not path or not filename or not os.path.isfile(path):
        abort(404)
    return send_file(path, as_attachment=True, download_name=filename, mimetype='text/csv')


@web_bp.route('/imports/templates/<string:template_kind>')
@roles_required('admin', 'writer')
def download_import_template(template_kind):
    try:
        language = request.args.get('language', 'technical')
        if language not in {'technical', 'ru'}:
            abort(400)
        content = '\ufeff' + csv_template(template_kind, language=language)
    except KeyError:
        abort(404)
    suffix = '_ru' if language == 'ru' else ''
    filename = f'{template_kind}_template{suffix}.csv'
    return Response(
        content,
        content_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


@web_bp.route('/processing/<processing_type>')
def processing_selection(processing_type):
    definition = get_processing(processing_type)
    if definition is None or not definition.available:
        return jsonify(error='Неизвестный вид обработки'), 404
    return render_template(
        'processing_selection.html',
        processing_type=processing_type,
        processing_label=definition.label,
        processing_definition=definition,
        materials=Material.query.order_by(Material.name).all(),
        tools=Tool.query.filter_by(processing_type=processing_type).order_by(Tool.name).all(),
        coatings=Coating.query.order_by(Coating.name).all(),
    )


@web_bp.route('/')
def select_parameters():
    unique_materials = Material.query.join(RecommendationParameter).distinct().all()
    unique_tools = Tool.query.join(RecommendationParameter).distinct().all()
    unique_coatings = Coating.query.join(RecommendationParameter).distinct().all()

    return render_template(
        'home.html',
        unique_materials=unique_materials,
        unique_tools=unique_tools,
        unique_coatings=unique_coatings,
        processing_types=PROCESSING_TYPES,
        future_processing_types=FUTURE_PROCESSING_TYPES,
    )


@web_bp.route('/recommended_speed', methods=['POST', 'GET'])
def recommended_speed():
    # Получаем значения фильтров из параметров запроса
    material_id = request.args.get('material_id', type=int)
    coating_id = request.args.get('coating_id', type=int)
    tool_id = request.args.get('tool_id', type=int)

    # Получаем списки для выпадающих списков
    materials = Material.query.join(RecommendationParameter).distinct().all()
    coatings = Coating.query.join(RecommendationParameter).distinct().all()
    tools = Tool.query.join(RecommendationParameter).distinct().all()

    # Формируем запрос с учетом фильтров
    query = RecommendationParameter.query.options(
        joinedload(RecommendationParameter.material),
        joinedload(RecommendationParameter.tool),
        joinedload(RecommendationParameter.coating))
    if material_id:
        query = query.filter_by(material_id=material_id)
    if coating_id:
        query = query.filter_by(coating_id=coating_id)
    if tool_id:
        query = query.filter_by(tool_id=tool_id)

    recommendations = query.all()

    return render_template('recommend_speed.html',
                           recommendations=recommendations,
                           materials=materials,
                           coatings=coatings,
                           tools=tools,
                           selected_material_id=material_id,
                           selected_coating_id=coating_id,
                           selected_tool_id=tool_id)


@web_bp.route('/add', methods=['POST', 'GET'])
@roles_required('admin', 'writer')
def add():
    material_form = MaterialForm()
    coating_form = CoatingForm()
    milling_geometry_form = MillingGeometryForm()
    turning_form = TurningGeometryForm()
    drill_form = DrillGeometryForm()
    tap_form = TapForm()

    if request.method == 'POST':
        try:
            if material_form.submit.data and material_form.validate_on_submit():
                if material_form.new_type.data:
                    existing_type = MaterialType.query.filter_by(name=material_form.new_type.data).first()
                    if existing_type:
                        type_id = existing_type.id
                    else:
                        new_material_type = MaterialType(name=material_form.new_type.data)
                        db.session.add(new_material_type)
                        db.session.commit()
                        type_id = new_material_type.id
                else:
                    type_id = material_form.type_id.data

                if type_id == 0:
                    material_form.type_id.errors.append('Пожалуйста, выберите тип материала или добавьте новый.')
                    render_template('add.html', material_form=material_form, coating_form=coating_form,
                                    tool_form=milling_geometry_form)

                new_material = Material(
                    name=material_form.name.data,
                    prop_physics=material_form.prop_physics.data,
                    structure=material_form.structure.data,
                    properties=material_form.properties.data,
                    gost=material_form.gost.data,
                    type_id=type_id  # Сохранение типа материала
                )
                db.session.add(new_material)
                db.session.commit()
                return redirect('/add')

            if coating_form.submit.data and coating_form.validate_on_submit():
                new_coating = Coating(
                    name=coating_form.name.data,
                    material_coating=coating_form.material_coating.data,
                    type_application=coating_form.type_application.data,
                    max_thickness=coating_form.max_thickness.data,
                    nano_hardness=coating_form.nanohardness.data,
                    temperature_resistance=coating_form.temperature_resistance.data,
                    coefficient_friction=coating_form.koefficient_friction.data,
                    color_coating=coating_form.color_coating.data
                )
                db.session.add(new_coating)
                db.session.commit()
                return redirect('/add')

            if milling_geometry_form.submit.data:
                if milling_geometry_form.validate_on_submit():
                    new_tool = Tool(
                        name=milling_geometry_form.name.data,
                        name_easy=milling_geometry_form.name_easy.data,
                        tool_type=milling_geometry_form.tool_type,
                        material_tool=milling_geometry_form.material_tool.data,
                        is_indexable=milling_geometry_form.is_indexable.data
                    )
                    new_milling_geometry = MillingGeometry(
                        type_milling=milling_geometry_form.type_milling.data,
                        diameter=milling_geometry_form.diameter.data,
                        diameter_shank=milling_geometry_form.diameter_shank.data,
                        length=milling_geometry_form.length.data,
                        length_work=milling_geometry_form.length_work.data,
                        number_teeth=milling_geometry_form.number_teeth.data,
                        spiral_angle=milling_geometry_form.spiral_angle.data,
                        type_shank=milling_geometry_form.type_shank.data
                    )

                    new_tool.milling_geometry = new_milling_geometry
                    if milling_geometry_form.insert.data:
                        new_tool.insert.append(Insert(name=milling_geometry_form.insert.data))
                    db.session.add(new_tool)
                    db.session.commit()
                    return redirect('/add')
                else:
                    flash('Исправьте ошибки в форме фрезы.', 'danger')

            if turning_form.submit.data and turning_form.validate_on_submit():
                new_tool = Tool(
                    name=turning_form.name.data,
                    name_easy=turning_form.name_easy.data,
                    tool_type=turning_form.tool_type,
                    material_tool=turning_form.material_tool.data,
                    is_indexable=turning_form.is_indexable.data,
                )
                new_tool.turning_geometry = TurningGeometry(
                    turning_type=turning_form.turning_type.data,
                    front_angle=turning_form.front_angle.data,
                    main_rear_angle=turning_form.main_rear_angle.data,
                    sharpening_angle=turning_form.sharpening_angle.data,
                    cutting_angle=turning_form.cutting_angle.data,
                    aux_rear_angle=turning_form.aux_rear_angle.data,
                )
                if turning_form.insert.data:
                    new_tool.insert.append(Insert(name=turning_form.insert.data))
                db.session.add(new_tool)
                db.session.commit()
                return redirect('/add')

            if drill_form.submit.data and drill_form.validate_on_submit():
                new_tool = Tool(
                    name=drill_form.name.data,
                    name_easy=drill_form.name_easy.data,
                    tool_type=drill_form.tool_type,
                    material_tool=drill_form.material_tool.data,
                    is_indexable=drill_form.is_indexable.data,
                )
                new_tool.drill_geometry = DrillGeometry(
                    drill_type=drill_form.drill_type.data,
                    diameter=drill_form.diameter.data,
                    screw_angle=drill_form.screw_angle.data,
                    top_angle=drill_form.top_angle.data,
                    front_angle=drill_form.front_angle.data,
                    rear_angle=drill_form.rear_angle.data,
                    transverse_edge_angle=drill_form.transverse_edge_angle.data,
                )
                if drill_form.insert.data:
                    new_tool.insert.append(Insert(name=drill_form.insert.data))
                db.session.add(new_tool)
                db.session.commit()
                return redirect('/add')

            if tap_form.submit.data and tap_form.validate_on_submit():
                tap = Tool(
                    name=tap_form.name.data,
                    name_easy=tap_form.name_easy.data or tap_form.name.data,
                    tool_type='tap',
                    processing_type='threading',
                    material_tool=tap_form.material_tool.data,
                    is_indexable=False,
                )
                tap.tap_geometry = TapGeometry(
                    thread_standard=tap_form.thread_standard.data,
                    thread_diameter=tap_form.thread_diameter.data,
                    pitch=tap_form.pitch.data,
                )
                db.session.add(tap)
                db.session.commit()
                return redirect('/add')

        except Exception as e:
            db.session.rollback()
            flash('Не удалось сохранить данные. Проверьте уникальность названия и значения полей.', 'danger')

    return render_template('add.html', material_form=material_form, coating_form=coating_form,
                           milling_geometry_form=milling_geometry_form, turning_form=turning_form,
                           drill_form=drill_form, tap_form=tap_form,
                           selected_tool_type=request.args.get('tool_type', 'milling'))


@web_bp.route('/materials', methods=['GET', 'POST'])
def materials_table():
    # Получаем все типы материалов для выпадающего списка
    material_types = MaterialType.query.all()

    # Параметры фильтрации и поиска
    selected_type_id = request.args.get('type_id')
    search_query = request.args.get('search_query', '')

    # Базовый запрос
    materials_query = Material.query

    # Фильтрация по типу материала, если выбран
    if selected_type_id and selected_type_id != 'all':
        materials_query = materials_query.filter_by(type_id=selected_type_id)

    # Поиск по названию материала
    if search_query:
        materials_query = materials_query.filter(Material.name.ilike(f'%{search_query}%'))

    pagination = materials_query.order_by(Material.name).paginate(
        page=request.args.get('page', 1, type=int), per_page=20, error_out=False
    )

    return render_template('materials.html', materials=pagination.items, pagination=pagination,
                           material_types=material_types, selected_type_id=selected_type_id, search_query=search_query)


@web_bp.route('/materials/search')
def search_materials():
    search_query = request.args.get('search_query', '')
    type_id = request.args.get('type_id', 'all')

    materials = Material.query
    # Ищем материалы, соответствующие запросу
    if type_id != 'all':
        materials = materials.filter_by(type_id=type_id)
    if search_query:
        filtered_materials = [material for material in materials.all() if search_query.lower() in material.name.lower()]
    else:
        filtered_materials = materials.all()

    # Преобразуем результат в список словарей
    materials_list = [{
        'id': material.id,
        'name': material.name,
        'prop_physics': material.prop_physics,
        'structure': material.structure,
        'properties': material.properties,
        'gost': material.gost
    } for material in filtered_materials]

    return jsonify(materials_list)


@web_bp.route('/materials/by_type/<int:type_id>')
def get_materials_by_type(type_id):
    # Получаем материалы, соответствующие выбранному типу
    materials = Material.query.filter_by(type_id=type_id).all()
    # Преобразуем материалы в список словарей
    materials_list = [{'id': material.id, 'name': material.name} for material in materials]
    return jsonify(materials_list)


@web_bp.route('/calculate')
def calculate():
    cutting_speed_value = request.args.get('cutting_speed', '0')
    try:
        cutting_speed = float(cutting_speed_value)  # Пробуем преобразовать в float
    except ValueError:
        return jsonify(error='cutting_speed должен быть числом больше нуля'), 400

    feed_per_tooth_value = request.args.get('feed_per_tooth', '0')
    try:
        feed_per_tooth = float(feed_per_tooth_value)
    except ValueError:
        return jsonify(error='feed_per_tooth должен быть числом больше нуля'), 400

    if cutting_speed <= 0 or feed_per_tooth <= 0:
        return jsonify(error='cutting_speed и feed_per_tooth должны быть больше нуля'), 400

    material_id = request.args.get('material_id')
    tool_id = request.args.get('tool_id')
    coating_id = request.args.get('coating_id')

    # Получаем коэффициенты из базы данных
    coefficient = Coefficient.query.filter_by(
        material_id=material_id,
        tool_id=tool_id,
        coating_id=coating_id
    ).first()

    # Если коэффициенты не найдены, возвращаем пустой результат
    if not coefficient:
        return jsonify({
            'cutting_force': 0,
            'cutting_temperature': 0,
            'tool_life': 0
        })

    result = calculate_cutting_parameters(
        force_coefficient=coefficient.cutting_force_coefficient,
        temperature_coefficient=coefficient.cutting_temperature_coefficient,
        durability_coefficient=coefficient.durability_coefficient,
        cutting_speed=cutting_speed,
        feed_per_tooth=feed_per_tooth,
    )

    return jsonify({
        'cutting_force': result.cutting_force,
        'cutting_temperature': result.cutting_temperature,
        'tool_life': result.tool_life,
    })


@web_bp.route('/api/cutting-reference')
def cutting_reference():
    """Возвращает исходные режимы и Kienzle-коэффициенты выбранной тройки."""

    material_id = request.args.get('material_id', type=int)
    tool_id = request.args.get('tool_id', type=int)
    coating_id = request.args.get('coating_id', type=int)
    if not all((material_id, tool_id, coating_id)):
        return jsonify(error='material_id, tool_id и coating_id обязательны'), 400

    reference = get_cutting_reference(material_id, tool_id, coating_id)
    if reference is None:
        return jsonify(found=False, reference={})
    return jsonify(found=True, reference=reference.as_dict())


@web_bp.route('/api/calculate/<processing_type>', methods=['POST'])
def calculate_processing(processing_type):
    """Рассчитывает базовые режимы по контракту выбранной операции."""

    if not is_available_processing(processing_type):
        return jsonify(error='Для этого вида обработки расчёт ещё не реализован.'), 400
    payload = request.get_json(silent=True) or request.form.to_dict()
    reference = get_cutting_reference(
        payload.get('material_id'),
        payload.get('tool_id'),
        payload.get('coating_id'),
    )
    reference_data = reference.as_dict() if reference else {}

    def value_or_reference(name: str):
        value = payload.get(name)
        return value if value not in (None, '') else reference_data.get(name)

    try:
        if processing_type == 'milling':
            result = calculate_milling(
                cutting_speed=value_or_reference('cutting_speed') or value_or_reference('base_cutting_speed'),
                diameter=payload.get('diameter'),
                number_teeth=payload.get('number_teeth'),
                feed_per_tooth=payload.get('feed_per_tooth'),
                base_feed_per_tooth=value_or_reference('base_feed_per_tooth'),
                operation_factor=payload.get('operation_factor'),
                depth_cut=payload.get('depth_cut'),
                width_cut=payload.get('width_cut'),
                coolant=payload.get('coolant'),
                material=payload.get('material') or reference_data.get('material_name'),
                coolant_factor=payload.get('coolant_factor'),
                kc1=value_or_reference('kc1'),
                mc=value_or_reference('mc'),
                chip_thickness=payload.get('chip_thickness'),
                rake_angle=value_or_reference('rake_angle'),
                max_rpm=payload.get('max_rpm'),
                machine_power=payload.get('machine_power'),
            )
        elif processing_type == 'turning':
            result = calculate_turning(
                cutting_speed=payload.get('cutting_speed'),
                base_cutting_speed=value_or_reference('base_cutting_speed'),
                diameter=payload.get('diameter'),
                feed_per_revolution=payload.get('feed_per_revolution') or reference_data.get('base_feed_per_revolution'),
                roughness=payload.get('roughness'),
                nose_radius=payload.get('nose_radius'),
                depth_cut=payload.get('depth_cut'),
                approach_angle=payload.get('approach_angle'),
                rake_angle=value_or_reference('rake_angle'),
                kc1=value_or_reference('kc1'),
                mc=value_or_reference('mc'),
                tool_factor=payload.get('tool_factor'),
                operation_factor=payload.get('operation_factor'),
                coolant_factor=payload.get('coolant_factor'),
                stiffness_factor=payload.get('stiffness_factor'),
                stock_allowance=payload.get('stock_allowance'),
                length_cut=payload.get('length_cut'),
                max_rpm=payload.get('max_rpm'),
                machine_power=payload.get('machine_power'),
                coolant=payload.get('coolant'),
                material=payload.get('material') or reference_data.get('material_name'),
            )
        else:
            result = calculate_threading(
                cutting_speed=payload.get('cutting_speed'),
                diameter=payload.get('diameter'),
                pitch=payload.get('pitch'),
                max_rpm=payload.get('max_rpm'),
                coolant=payload.get('coolant'),
                material=payload.get('material'),
            )
    except CalculationInputError as error:
        return jsonify(error=str(error)), 400
    return jsonify(result.as_dict())


@web_bp.route('/materials/<int:material_id>/delete', methods=['POST'])
@roles_required('admin', 'writer')
def delete_materials(material_id):
    if not DeleteConfirmationForm().validate_on_submit():
        flash('Не удалось подтвердить удаление материала.', 'danger')
        return redirect('/materials')
    entity_to_delete = Material.query.get_or_404(material_id)
    try:
        db.session.delete(entity_to_delete)
        db.session.commit()
        flash('Материал удалён.', 'success')
        return redirect('/materials')
    except Exception:
        db.session.rollback()
        flash('Не удалось удалить материал: он может использоваться в других записях.', 'danger')
        return redirect('/materials')


@web_bp.route('/materials/<int:material_id>/update', methods=['GET', 'POST'])
@roles_required('admin', 'writer')
def materials_update(material_id):
    material_form = MaterialForm()
    material = Material.query.get_or_404(material_id)
    if request.method == 'POST':
        try:
            if material_form.submit.data and material_form.validate_on_submit():
                if material_form.new_type.data:
                    existing_type = MaterialType.query.filter_by(name=material_form.new_type.data).first()
                    if existing_type:
                        type_id = existing_type.id
                    else:
                        new_material_type = MaterialType(name=material_form.new_type.data)
                        db.session.add(new_material_type)
                        db.session.commit()
                        type_id = new_material_type.id
                else:
                    type_id = material_form.type_id.data

                if type_id == 0:
                    material_form.type_id.errors.append('Пожалуйста, выберите тип материала или добавьте новый.')
                    return render_template('materials_update.html',
                                           material=material,
                                           material_form=material_form)

                material.name = material_form.name.data
                material.prop_physics = material_form.prop_physics.data
                material.structure = material_form.structure.data
                material.properties = material_form.properties.data
                material.gost = material_form.gost.data
                material.type_id = type_id

                db.session.commit()
                return redirect('/materials')
        except Exception as e:
            return f'Ошибка: {e}'

    material_form.type_id.data = material.type_id
    return render_template('materials_update.html',
                           material=material,
                           material_form=material_form)


@web_bp.route("/material/<int:material_id>/info")
def mat_info(material_id):
    material = Material.query.get_or_404(material_id)
    return render_template('mat_info.html', material=material)


@web_bp.route('/coatings')
def coatings():
    search_query = request.args.get('search_query', '')
    query = Coating.query
    if search_query:
        query = query.filter(Coating.name.ilike(f'%{search_query}%'))
    pagination = query.order_by(Coating.name).paginate(page=request.args.get('page', 1, type=int), per_page=20, error_out=False)
    return render_template('coating.html', coatings=pagination.items, pagination=pagination, search_query=search_query)


@web_bp.route('/coating/<int:coating_id>/delete', methods=['POST'])
@roles_required('admin', 'writer')
def delete_coating(coating_id):
    if not DeleteConfirmationForm().validate_on_submit():
        flash('Не удалось подтвердить удаление покрытия.', 'danger')
        return redirect('/coatings')
    entity_to_delete = Coating.query.get_or_404(coating_id)
    try:
        db.session.delete(entity_to_delete)
        db.session.commit()
        flash('Покрытие удалено.', 'success')
        return redirect('/coatings')
    except Exception:
        db.session.rollback()
        flash('Не удалось удалить покрытие: оно может использоваться в других записях.', 'danger')
        return redirect('/coatings')


@web_bp.route('/coating/<int:coating_id>/update', methods=['GET', 'POST'])
@roles_required('admin', 'writer')
def coating_update(coating_id):
    coating = Coating.query.get(coating_id)
    coating_form = CoatingForm()
    if request.method == 'POST':
        try:
            if coating_form.submit.data and coating_form.validate_on_submit():
                coating.name = coating_form.name.data
                coating.material_coating = coating_form.material_coating.data
                coating.max_thickness = coating_form.max_thickness.data
                coating.nano_hardness = coating_form.nanohardness.data
                coating.temperature_resistance = coating_form.temperature_resistance.data
                coating.coefficient_friction = coating_form.koefficient_friction.data
                coating.color_coating = coating_form.color_coating.data

                db.session.commit()
                return redirect('/coatings')
            else:
                return render_template('coating_update.html', coating=coating, coating_form=coating_form)
        except Exception as e:
            return f'Ошибка: {e}'

    return render_template('coating_update.html', coating=coating, coating_form=coating_form)


@web_bp.route("/coating/<int:coating_id>/info")
def coat_info(coating_id):
    coating = Coating.query.get_or_404(coating_id)
    return render_template('coat_info.html', coating=coating)


@web_bp.route('/tools')
def tools():
    # Получаем параметры запроса
    tool_type = request.args.get('tool_type', 'all')
    search_query = request.args.get('search_query', '')

    # Оптимизация запроса с подгрузкой связанных геометрий
    query = Tool.query.options(
        db.joinedload(Tool.milling_geometry),
        db.joinedload(Tool.turning_geometry),
        db.joinedload(Tool.drill_geometry),
        db.joinedload(Tool.tap_geometry),
    )

    # Фильтрация по типу инструмента
    if tool_type != 'all':
        query = query.filter(Tool.tool_type == tool_type)

    if search_query:
        query = query.filter(Tool.name.ilike(f'%{search_query}%'))
    pagination = query.order_by(Tool.name).paginate(page=request.args.get('page', 1, type=int), per_page=20, error_out=False)

    return render_template('tools.html', tools=pagination.items, pagination=pagination,
                           selected_tool_type=tool_type, search_query=search_query)


@web_bp.route('/catalog/milling-cutters')
def milling_cutters_catalog():
    pagination = Tool.query.filter_by(processing_type='milling').order_by(Tool.name).paginate(
        page=request.args.get('page', 1, type=int), per_page=20, error_out=False
    )
    return render_template('tool_catalog.html', title='Фрезы', items=pagination.items, pagination=pagination, item_type='tool')


@web_bp.route('/catalog/inserts')
def inserts_catalog():
    pagination = Insert.query.order_by(Insert.name).paginate(
        page=request.args.get('page', 1, type=int), per_page=20, error_out=False
    )
    return render_template('tool_catalog.html', title='Режущие пластины', items=pagination.items, pagination=pagination, item_type='insert')


@web_bp.route('/catalog/inserts/add', methods=['GET', 'POST'])
@roles_required('admin', 'writer')
def add_insert():
    form = InsertForm()
    if form.validate_on_submit():
        insert = Insert(
            name=form.name.data,
            material=form.material.data,
            geometry=form.geometry.data,
            rake_angle=form.rake_angle.data,
            relief_angle=form.relief_angle.data,
        )
        db.session.add(insert)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Не удалось добавить пластину: такое обозначение уже существует.', 'danger')
        else:
            flash('Режущая пластина добавлена.', 'success')
            return redirect(url_for('web.inserts_catalog'))
    return render_template('insert_form.html', form=form)


@web_bp.route('/catalog/taps')
def taps_catalog():
    pagination = Tool.query.filter_by(processing_type='threading').order_by(Tool.name).paginate(
        page=request.args.get('page', 1, type=int), per_page=20, error_out=False
    )
    return render_template('tool_catalog.html', title='Метчики', items=pagination.items, pagination=pagination, item_type='tap')


@web_bp.route('/catalog/taps/add', methods=['GET', 'POST'])
@roles_required('admin', 'writer')
def add_tap():
    form = TapForm()
    if form.validate_on_submit():
        tap = Tool(
            name=form.name.data,
            name_easy=form.name_easy.data or form.name.data,
            material_tool=form.material_tool.data,
            tool_type='tap',
            processing_type='threading',
        )
        tap.tap_geometry = TapGeometry(
            thread_standard=form.thread_standard.data,
            thread_diameter=form.thread_diameter.data,
            pitch=form.pitch.data,
        )
        db.session.add(tap)
        db.session.commit()
        flash('Метчик добавлен.', 'success')
        return redirect(url_for('web.taps_catalog'))
    return render_template('tap_form.html', form=form)


@web_bp.route('/tool/<int:tool_id>/delete', methods=['POST'])
@roles_required('admin', 'writer')
def delete_tool(tool_id):
    if not DeleteConfirmationForm().validate_on_submit():
        flash('Не удалось подтвердить удаление инструмента.', 'danger')
        return redirect('/tools')
    entity_to_delete = Tool.query.get_or_404(tool_id)
    tool_geometry = [getattr(entity_to_delete, 'milling_geometry'),
                     getattr(entity_to_delete, 'turning_geometry'),
                     getattr(entity_to_delete, 'drill_geometry'),
                     getattr(entity_to_delete, 'tap_geometry')]

    try:
        db.session.delete(entity_to_delete)
        for geom in tool_geometry:
            if geom:
                db.session.delete(geom)
        for insert in entity_to_delete.insert:
            db.session.delete(insert)
        db.session.commit()
        flash('Инструмент удалён.', 'success')
        return redirect('/tools')
    except Exception:
        db.session.rollback()
        flash('Не удалось удалить инструмент: он может использоваться в других записях.', 'danger')
        return redirect('/tools')


@web_bp.route('/inserts/<int:insert_id>/delete', methods=['POST'])
@roles_required('admin', 'writer')
def delete_insert(insert_id):
    if not DeleteConfirmationForm().validate_on_submit():
        flash('Не удалось подтвердить удаление пластины.', 'danger')
        return redirect(url_for('web.inserts_catalog'))

    insert = Insert.query.get_or_404(insert_id)
    try:
        db.session.delete(insert)
        db.session.commit()
        flash('Режущая пластина удалена.', 'success')
    except Exception:
        db.session.rollback()
        flash('Не удалось удалить режущую пластину.', 'danger')
    return redirect(url_for('web.inserts_catalog'))


@web_bp.route('/tool/<int:tool_id>/update', methods=['GET', 'POST'])
@roles_required('admin', 'writer')
def tool_update(tool_id):
    tool = Tool.query.get_or_404(tool_id)

    # Определяем, какую форму использовать в зависимости от типа инструмента
    if tool.tool_type == 'milling':
        form = MillingGeometryForm()
    elif tool.tool_type == 'turning':
        form = TurningGeometryForm()
    elif tool.tool_type == 'drilling':
        form = DrillGeometryForm()
    elif tool.tool_type == 'tap':
        form = TapForm()
    else:
        form = ToolForm()

    if request.method == 'GET':
        # Предзаполняем форму данными инструмента
        form.name.data = tool.name
        form.material_tool.data = tool.material_tool
        form.name_easy.data = tool.name_easy
        if 'is_indexable' in form._fields:
            form.is_indexable.data = tool.is_indexable

        # Предзаполняем данные геометрии инструмента
        if tool.tool_type == 'milling' and tool.milling_geometry:
            form.type_milling.data = tool.milling_geometry.type_milling
            form.diameter.data = tool.milling_geometry.diameter
            form.diameter_shank.data = tool.milling_geometry.diameter_shank
            form.length.data = tool.milling_geometry.length
            form.length_work.data = tool.milling_geometry.length_work
            form.number_teeth.data = tool.milling_geometry.number_teeth
            form.type_shank.data = tool.milling_geometry.type_shank
            form.spiral_angle.data = tool.milling_geometry.spiral_angle
        elif tool.tool_type == 'turning' and tool.turning_geometry:
            form.turning_type.data = tool.turning_geometry.turning_type
            form.front_angle.data = tool.turning_geometry.front_angle
            form.main_rear_angle.data = tool.turning_geometry.main_rear_angle
            form.sharpening_angle.data = tool.turning_geometry.sharpening_angle
            form.cutting_angle.data = tool.turning_geometry.cutting_angle
            form.aux_rear_angle.data = tool.turning_geometry.aux_rear_angle
        elif tool.tool_type == 'drilling' and tool.drill_geometry:
            form.drill_type.data = tool.drill_geometry.drill_type
            form.diameter.data = tool.drill_geometry.diameter
            form.screw_angle.data = tool.drill_geometry.screw_angle
            form.top_angle.data = tool.drill_geometry.top_angle
            form.front_angle.data = tool.drill_geometry.front_angle
            form.rear_angle.data = tool.drill_geometry.rear_angle
            form.transverse_edge_angle.data = tool.drill_geometry.transverse_edge_angle
        elif tool.tool_type == 'tap' and tool.tap_geometry:
            form.thread_standard.data = tool.tap_geometry.thread_standard
            form.thread_diameter.data = tool.tap_geometry.thread_diameter
            form.pitch.data = tool.tap_geometry.pitch

    elif form.validate_on_submit():
        # Обновляем основные поля инструмента
        tool.name = form.name.data
        tool.material_tool = form.material_tool.data
        tool.name_easy = form.name_easy.data
        if 'is_indexable' in form._fields:
            tool.is_indexable = form.is_indexable.data

        # Обновляем данные геометрии инструмента
        if tool.tool_type == 'milling':
            if not tool.milling_geometry:
                tool.milling_geometry = MillingGeometry()
            tool.milling_geometry.type_milling = form.type_milling.data
            tool.milling_geometry.diameter = form.diameter.data
            tool.milling_geometry.diameter_shank = form.diameter_shank.data
            tool.milling_geometry.length = form.length.data
            tool.milling_geometry.length_work = form.length_work.data
            tool.milling_geometry.number_teeth = form.number_teeth.data
            tool.milling_geometry.type_shank = form.type_shank.data
            tool.milling_geometry.spiral_angle = form.spiral_angle.data
        elif tool.tool_type == 'turning':
            if not tool.turning_geometry:
                tool.turning_geometry = TurningGeometry()
            tool.turning_geometry.turning_type = form.turning_type.data
            tool.turning_geometry.front_angle = form.front_angle.data
            tool.turning_geometry.main_rear_angle = form.main_rear_angle.data
            tool.turning_geometry.sharpening_angle = form.sharpening_angle.data
            tool.turning_geometry.cutting_angle = form.cutting_angle.data
            tool.turning_geometry.aux_rear_angle = form.aux_rear_angle.data
        elif tool.tool_type == 'drilling':
            if not tool.drill_geometry:
                tool.drill_geometry = DrillGeometry()
            tool.drill_geometry.drill_type = form.drill_type.data
            tool.drill_geometry.diameter = form.diameter.data
            tool.drill_geometry.screw_angle = form.screw_angle.data
            tool.drill_geometry.top_angle = form.top_angle.data
            tool.drill_geometry.front_angle = form.front_angle.data
            tool.drill_geometry.rear_angle = form.rear_angle.data
            tool.drill_geometry.transverse_edge_angle = form.transverse_edge_angle.data
        elif tool.tool_type == 'tap':
            if not tool.tap_geometry:
                tool.tap_geometry = TapGeometry()
            tool.tap_geometry.thread_standard = form.thread_standard.data
            tool.tap_geometry.thread_diameter = form.thread_diameter.data
            tool.tap_geometry.pitch = form.pitch.data

        try:
            db.session.commit()
            flash('Инструмент успешно обновлен!', 'success')
            return redirect(url_for('web.tools'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении инструмента: {e}', 'danger')
    else:
        if request.method == 'POST':
            flash('Пожалуйста, исправьте ошибки в форме.', 'danger')

    return render_template('tool_update.html', form=form, tool=tool)


@web_bp.route("/tool/<int:tool_id>/info")
def tools_info(tool_id):
    tool = Tool.query.get_or_404(tool_id)
    return render_template('tool_info.html', tool=tool)


@web_bp.route('/experiments')
def experiments_table():
    material_filter = request.args.get('material', '')
    coating_filter = request.args.get('coating', '')
    spindle_min = request.args.get('spindle_min', type=float)
    spindle_max = request.args.get('spindle_max', type=float)
    feed_min = request.args.get('feed_min', type=float)
    feed_max = request.args.get('feed_max', type=float)
    sort_by = request.args.get('sort_by')
    order = request.args.get('order', 'asc')

    experiments_query = Experiment.query.options(joinedload(Experiment.material), joinedload(Experiment.coating),
                                                  joinedload(Experiment.tool))
    if current_user.is_authenticated and current_user.role == 'reader':
        experiments_query = experiments_query.filter(Experiment.publication_status == 'published')
    experiments_query = experiments_query.all()

    # Фильтрация уже в Python
    if material_filter:
        experiments_query = [exp for exp in experiments_query if material_filter.lower() in exp.material.name.lower()]

    if coating_filter:
        experiments_query = [exp for exp in experiments_query if coating_filter.lower() in exp.coating.name.lower()]

    if spindle_min:
        experiments_query = [exp for exp in experiments_query if exp.spindle_speed >= spindle_min]

    if spindle_max:
        experiments_query = [exp for exp in experiments_query if exp.spindle_speed <= spindle_max]

    if feed_min:
        experiments_query = [exp for exp in experiments_query if exp.feed_table >= feed_min]

    if feed_max:
        experiments_query = [exp for exp in experiments_query if exp.feed_table <= feed_max]

    sortable_fields = {'spindle_speed', 'feed_table', 'length_path', 'durability', 'data_experiment'}
    if sort_by in sortable_fields:
        reverse = (order == 'desc')
        experiments_query = sorted(experiments_query, key=lambda x: getattr(x, sort_by), reverse=reverse)

    page = request.args.get('page', 1, type=int)
    per_page = 20
    total = len(experiments_query)
    pagination = type('PaginationInfo', (), {
        'page': page,
        'pages': max(1, (total + per_page - 1) // per_page),
        'has_prev': page > 1,
        'has_next': page * per_page < total,
        'prev_num': page - 1,
        'next_num': page + 1,
    })()
    return render_template('experiment.html',
                           experiment=experiments_query[(page - 1) * per_page:page * per_page],
                           pagination=pagination,
                           sort_by=sort_by,
                           order=order,
                           request_args=request.args)


@web_bp.route('/experiments/reference')
def experiments_reference_graphs():
    return render_template('reference_graphs.html')


@web_bp.route('/experiments/<int:experiment_id>/delete', methods=['POST'])
@roles_required('admin', 'writer')
def delete_experiment(experiment_id):
    if not DeleteConfirmationForm().validate_on_submit():
        flash('Не удалось подтвердить удаление эксперимента.', 'danger')
        return redirect('/experiments')
    experiment: Experiment = Experiment.query.get_or_404(experiment_id)
    wear_table: list[WearMeasurement] = WearMeasurement.query.filter_by(experiment_id=experiment_id).all()
    for row in wear_table:
        db.session.delete(row)
    db.session.delete(experiment)
    try:
        db.session.commit()
        flash('Эксперимент удалён.', 'success')
        return redirect('/experiments')
    except Exception:
        db.session.rollback()
        flash('Не удалось удалить эксперимент.', 'danger')
        return redirect('/experiments')


@web_bp.route('/experiment/add', methods=['GET', 'POST'])
@roles_required('admin', 'writer')
def add_experiment():
    form = ExperimentForm()
    if request.method == 'POST':
        wear_entry_count = len([key for key in request.form.keys() if 'wear_data-' in key and '-length' in key])
        form.wear_data.min_entries = wear_entry_count
        form = ExperimentForm(request.form)

        if form.validate():
            new_experiment = Experiment(
                material_id=form.material_id.data,
                tool_id=form.tool_id.data,
                coating_id=form.coating_id.data,
                spindle_speed=form.spindle_speed.data,
                feed_table=form.feed_table.data,
                depth_cut=form.depth_cut.data,
                width_cut=form.width_cut.data,
                length_path=form.length_path.data,
                durability=form.durability.data,
                data_experiment=form.date_conducted.data
            )
            db.session.add(new_experiment)
            db.session.flush()
            for wear_form in form.wear_data.entries:
                wear_entry = WearMeasurement(
                    experiment_id=new_experiment.id,
                    length=wear_form.form.length.data,
                    wear=wear_form.form.wear.data
                )
                db.session.add(wear_entry)
            db.session.commit()

            flash(f'Добавлен новый эксперимент: Номер - {new_experiment.id}', 'success')
            return redirect(url_for('web.experiments_info', experiment_id=new_experiment.id))
        else:
            print(form.errors)
    return render_template('add_experiment.html', form=form)


@web_bp.route("/experiments/<int:experiment_id>/info")
def experiments_info(experiment_id):
    experiment = Experiment.query.get_or_404(experiment_id)
    if (current_user.is_authenticated and current_user.role == 'reader'
            and experiment.publication_status != 'published'):
        abort(404)
    return render_template('experiment_info.html', experiment=experiment)


@web_bp.route("/adhesive")
def adhesive():
    materials_with_adhesion = Material.query.join(Adhesive).distinct().all()
    coatings_with_adhesion = Coating.query.join(Adhesive).distinct().all()
    available_temperatures = Adhesive.query.with_entities(Adhesive.temperature).distinct().all()

    selected_material = request.args.get('material_id')
    selected_coating = request.args.get('coating_id')
    selected_temperature = request.args.get('temperature')

    query = Adhesive.query

    if selected_material:
        selected_material = int(selected_material)  # Преобразуем в целое число
        query = query.filter(Adhesive.material_id == selected_material)
    else:
        selected_material = None

    if selected_coating:
        selected_coating = int(selected_coating)  # Преобразуем в целое число
        query = query.filter(Adhesive.coating_id == selected_coating)
    else:
        selected_coating = None

    if selected_temperature:
        selected_temperature = float(selected_temperature)  # Преобразуем в число с плавающей точкой
        query = query.filter(Adhesive.temperature == selected_temperature)
    else:
        selected_temperature = None

    adhesive_table = query.all()

    return render_template('adhesive.html',
                           adhesive=adhesive_table,
                           materials=materials_with_adhesion,
                           coatings=coatings_with_adhesion,
                           available_temperatures=available_temperatures,
                           selected_temperature=selected_temperature,
                           selected_coating=selected_coating,
                           selected_material=selected_material)


@web_bp.route("/expected_parameters", methods=['GET', 'POST'])
def expected_parameters():
    processing_type = request.args.get('processing_type', 'milling')
    if not is_available_processing(processing_type):
        processing_type = 'milling'

    materials = Material.query.order_by(Material.name).all()
    tools = Tool.query.filter_by(processing_type=processing_type).order_by(Tool.name).all()
    coatings = Coating.query.all()
    material_types = MaterialType.query.all()

    selected_material = request.args.get('material_id', type=int)
    selected_tool = request.args.get('tool_id', type=int)
    selected_coating = request.args.get('coating_id', type=int)
    # Серверная защита от устаревших ID: клиентский сброс не должен быть
    # единственной гарантией при ручном изменении query-параметров.
    if selected_material and db.session.get(Material, selected_material) is None:
        selected_material = None
    if selected_coating and db.session.get(Coating, selected_coating) is None:
        selected_coating = None
    if selected_tool:
        selected_tool_record = db.session.get(Tool, selected_tool)
        if selected_tool_record is None or selected_tool_record.processing_type != processing_type:
            selected_tool = None
    coefficient = None

    return render_template(
        'expected_parameters.html',
        materials=materials,
        tools=tools,
        coatings=coatings,
        coefficient=coefficient,
        selected_material=selected_material,
        selected_tool=selected_tool,
        selected_coating=selected_coating,
        material_types=material_types,
        processing_type=processing_type,
        processing_definition=get_processing(processing_type),
        processing_types=PROCESSING_TYPES,
    )


@web_bp.route('/update_graph_data', methods=['POST'])
def update_graph_data():
    data = request.get_json(silent=True) or {}
    try:
        material_id = int(data['material_id'])
        tool_id = int(data['tool_id'])
        coating_id = int(data['coating_id'])
    except (KeyError, TypeError, ValueError):
        return jsonify(status='error', error='material_id, tool_id и coating_id должны быть целыми числами'), 400

    tool = Tool.query.get(tool_id)
    if not tool or not tool.milling_geometry:
        return jsonify(status='error', error='Для расчёта требуется существующая фреза с геометрией'), 400
    diameter = tool.milling_geometry.diameter
    count_of_teeth = tool.milling_geometry.number_teeth
    if not diameter or diameter <= 0 or not count_of_teeth or count_of_teeth <= 0:
        return jsonify(status='error', error='Диаметр и число зубьев должны быть больше нуля'), 400

    coefficient: Coefficient = Coefficient.query.filter_by(
        material_id=material_id,
        tool_id=tool_id,
        coating_id=coating_id
    ).first()

    if not coefficient:
        session.pop('graph_data', None)
    else:
        session['graph_data'] = {
            'cutting_force_coefficient': coefficient.cutting_force_coefficient,
            'cutting_temperature_coefficient': coefficient.cutting_temperature_coefficient,
            'durability_coefficient': coefficient.durability_coefficient,
            'diameter': diameter,
            'teeth_count': count_of_teeth,
            'coating_id': coating_id,
            'material_name': coefficient.material.name,
            'tool_id': tool_id
        }

    # Получаем рекомендуемые режимы резания
    recommended = RecommendationParameter.query.filter_by(
        material_id=material_id,
        tool_id=tool_id,
        coating_id=coating_id
    ).first()

    if recommended:
        # Вычисляем дополнительные параметры
        cutting_speed = round(recommended.cutter_speed, 2)
        feed_per_tooth = round(recommended.feed_of_teeth, 3)
        cutting_force = recommended.Fz
        temperature = recommended.temperature
        durability = recommended.durability_

        recommended_data = {
            'spindle_speed': int(recommended.spindle_speed),
            'feed_rate': int(recommended.feed_table),
            'cutting_speed': round(cutting_speed, 2) if cutting_speed else None,
            'feed_per_tooth': round(feed_per_tooth, 3) if feed_per_tooth else None,
            'cutting_force': round(cutting_force, 2) if cutting_force else None,
            'temperature': round(temperature, 2) if temperature else None,
            'durability': round(durability, 2) if isinstance(durability, (int, float)) else durability
        }
    else:
        recommended_data = None

    return jsonify({'status': 'success', 'recommended_data': recommended_data})
