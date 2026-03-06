from __future__ import annotations

import os
import logging
import logging.config

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from nfdi_search_engine.extensions import limiter, session_ext, login_manager
from nfdi_search_engine.web.filters import register_filters
from nfdi_search_engine.web.errors import register_error_handlers
from nfdi_search_engine.web.auth.login import init_login_loader
from nfdi_search_engine.infra.elastic.client import get_es_client
from nfdi_search_engine.infra.elastic.indices import ensure_indices
from nfdi_search_engine.infra.store.in_memory_result_store import InMemoryTTLResultStore
from nfdi_search_engine.infra.jobs.inprocess_dispatcher import InProcessDispatcher
from nfdi_search_engine.infra.jobs.tracking_processor import TrackingProcessor
from nfdi_search_engine.infra.jobs.chatbot_processor import ChatbotProcessor
from nfdi_search_engine.services.user_service import UserService
from nfdi_search_engine.services.search_service import SearchService, SearchSettings
from nfdi_search_engine.services.chatbot_service import ChatbotService, ChatbotSettings
from nfdi_search_engine.services.tracking_service import TrackingService
from nfdi_search_engine.services.analytics_service import AnalyticsService
from nfdi_search_engine.services.publication_details_service import PublicationDetailsService, DetailsSettings


def create_app() -> Flask:
    logging.config.fileConfig(
        os.getenv("LOGGING_FILE_CONFIG", "./logging.conf")
    )
    logger = logging.getLogger("nfdi_search_engine")

    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

    app.config.from_object(Config)

    # register jinja filters
    register_filters(app)

    # Flask-Session
    session_ext.init_app(app)

    # Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "login"

    # Flask-Limiter
    limiter.init_app(app)

    # register error handlers
    register_error_handlers(app)

    # result store
    result_store = InMemoryTTLResultStore()

    # elastic client and setup
    es = get_es_client(
        Config.ELASTIC["server"],
        Config.ELASTIC["username"],
        Config.ELASTIC["password"],
    )
    ensure_indices(es)

    # background jobs‚
    tracking_tasks = TrackingProcessor(es)
    chatbot_tasks = ChatbotProcessor(
        result_store=result_store,
        settings=ChatbotSettings.from_config(app.config)
    )

    jobs = InProcessDispatcher(
        handlers={
            "tracking.activity.write": tracking_tasks.handle_write_activity,
            "tracking.search_term.write": tracking_tasks.handle_write_search_term,
            "tracking.user_agent.upsert": tracking_tasks.handle_upsert_user_agent,
            "tracking.event.write": tracking_tasks.handle_write_event,
            "tracking.visitor_id.propagate": tracking_tasks.handle_propagate_visitor_id,
            "chatbot.index_search_results": chatbot_tasks.handle_index_search_results,
        }
    )

    # services
    user_service = UserService(
        es_client=es,
        all_data_sources=list(app.config["DATA_SOURCES"].keys()),
        es_date_format=Config.DATE_FORMAT_FOR_ELASTIC,
    )

    tracking_service = TrackingService(
        es_client=es,
        jobs=jobs,
        es_date_format=Config.DATE_FORMAT_FOR_ELASTIC,
    )

    analytics_service = AnalyticsService(
        tracking_service=tracking_service,
        user_service=user_service,
        es_date_format=app.config["DATE_FORMAT_FOR_ELASTIC"],
    )

    chatbot_service = ChatbotService(
        settings=ChatbotSettings.from_config(app.config),
        activity=tracking_service,
        jobs=jobs,
    )

    search_service = SearchService(
        settings=SearchSettings.from_config(app.config),
        chatbot=chatbot_service,
        store=result_store,
        jobs=jobs,
        activity=tracking_service,
    )

    pub_details_service = PublicationDetailsService(
        settings=DetailsSettings.from_config(app.config),
    )

    # expose shared objects in app.extensions‚
    app.extensions["logger"] = logger
    app.extensions["result_store"] = result_store
    app.extensions["job_dispatcher"] = jobs
    app.extensions["es_client"] = es
    app.extensions["services"] = {
        "search": search_service,
        "users": user_service,
        "tracking": tracking_service,
        "analytics": analytics_service,
        "chatbot": chatbot_service,
        "publication_details": pub_details_service,
    }

    # register user loader
    init_login_loader()

    # register blueprints
    from nfdi_search_engine.web.public import bp as public_bp
    from nfdi_search_engine.web.search import bp as search_bp
    from nfdi_search_engine.web.control_panel import bp as control_panel_bp
    from nfdi_search_engine.web.auth import bp as auth_bp
    from nfdi_search_engine.web.tracking import bp as tracking_bp
    from nfdi_search_engine.web.account import bp as account_bp
    from nfdi_search_engine.web.chatbot import bp as chatbot_bp
    from nfdi_search_engine.web.details import bp as details_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(control_panel_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(details_bp)

    return app
