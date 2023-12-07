import os
import flask
from flask import (
    abort,
    current_app,
    _app_ctx_stack,
    _request_ctx_stack,
    request
)


FILTERED_ROUTES = ['static', 'superadmin', 'change_m_status']

__all__ = ['Maintenance']


class Maintenance:
    """
    Add Maintenance mode feature to your flask application.
    """

    def __init__(self, app=None):
        """
        :param app:
            Flask application object.
        """

        self.app = app

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        Initalizes the application with the extension.

        :param app:
            Flask application object.
        """

        app.before_request_funcs.setdefault(None, []).append(self._handler)

    def _handler(self):
        """
        Maintenance mode handler.
        """
        actx = _app_ctx_stack.top
        rctx = _request_ctx_stack.top

        if actx and rctx:
            if request.endpoint not in FILTERED_ROUTES:
                ins_path = os.path.join(current_app.instance_path,
                                        'under_maintenance')

                if os.path.exists(ins_path) and os.path.isfile(ins_path):
                    abort(503)

    def enable(self):
        """
        Enable Maintenance mode.
        """
        try:
            ins_path = current_app.instance_path

            if not os.path.exists(ins_path):
                os.makedirs(ins_path)

            open(os.path.join(ins_path, 'under_maintenance'), 'w').close()
            return True
        except Exception as e:
            return str(e)

    def disable(self):
        """
        Disable Maintenance mode.
        """
        ins_path = current_app.instance_path
        main_file = os.path.join(ins_path, 'under_maintenance')

        if os.path.exists(main_file) and os.path.isfile(main_file):
            try:
                os.remove(main_file)
                return True
            except Exception as e:
                return str(e)