# flake8: noqa

__all__ = [
    "ActorsApi",
    "AnalysesApi",
    "AnalysisGroupsApi",
    "BehaviorEventsApi",
    "BrandsApi",
    "EmailAnalysesApi",
    "ExecutionProfilesApi",
    "FaviconsApi",
    "IdentifiersApi",
    "InfrastructureApi",
    "InteractionsApi",
    "JavascriptFunctionsApi",
    "OperationsApi",
    "PayloadsApi",
    "PhishingKitsApi",
    "RequestsApi",
    "RulesApi",
    "SearchApi",
    "SignalsApi",
    "StatsApi",
    "TlsCertificatesApi",
    "UsageApi",
]

import typing as _typing

if _typing.TYPE_CHECKING:
    # import apis into api package
    from sandfish_sdk.generated.api.actors_api import ActorsApi
    from sandfish_sdk.generated.api.analyses_api import AnalysesApi
    from sandfish_sdk.generated.api.analysis_groups_api import AnalysisGroupsApi
    from sandfish_sdk.generated.api.behavior_events_api import BehaviorEventsApi
    from sandfish_sdk.generated.api.brands_api import BrandsApi
    from sandfish_sdk.generated.api.email_analyses_api import EmailAnalysesApi
    from sandfish_sdk.generated.api.execution_profiles_api import ExecutionProfilesApi
    from sandfish_sdk.generated.api.favicons_api import FaviconsApi
    from sandfish_sdk.generated.api.identifiers_api import IdentifiersApi
    from sandfish_sdk.generated.api.infrastructure_api import InfrastructureApi
    from sandfish_sdk.generated.api.interactions_api import InteractionsApi
    from sandfish_sdk.generated.api.javascript_functions_api import JavascriptFunctionsApi
    from sandfish_sdk.generated.api.operations_api import OperationsApi
    from sandfish_sdk.generated.api.payloads_api import PayloadsApi
    from sandfish_sdk.generated.api.phishing_kits_api import PhishingKitsApi
    from sandfish_sdk.generated.api.requests_api import RequestsApi
    from sandfish_sdk.generated.api.rules_api import RulesApi
    from sandfish_sdk.generated.api.search_api import SearchApi
    from sandfish_sdk.generated.api.signals_api import SignalsApi
    from sandfish_sdk.generated.api.stats_api import StatsApi
    from sandfish_sdk.generated.api.tls_certificates_api import TlsCertificatesApi
    from sandfish_sdk.generated.api.usage_api import UsageApi

else:
    from importlib import import_module

    _exports = {
        "ActorsApi": ".actors_api",
        "AnalysesApi": ".analyses_api",
        "AnalysisGroupsApi": ".analysis_groups_api",
        "BehaviorEventsApi": ".behavior_events_api",
        "BrandsApi": ".brands_api",
        "EmailAnalysesApi": ".email_analyses_api",
        "ExecutionProfilesApi": ".execution_profiles_api",
        "FaviconsApi": ".favicons_api",
        "IdentifiersApi": ".identifiers_api",
        "InfrastructureApi": ".infrastructure_api",
        "InteractionsApi": ".interactions_api",
        "JavascriptFunctionsApi": ".javascript_functions_api",
        "OperationsApi": ".operations_api",
        "PayloadsApi": ".payloads_api",
        "PhishingKitsApi": ".phishing_kits_api",
        "RequestsApi": ".requests_api",
        "RulesApi": ".rules_api",
        "SearchApi": ".search_api",
        "SignalsApi": ".signals_api",
        "StatsApi": ".stats_api",
        "TlsCertificatesApi": ".tls_certificates_api",
        "UsageApi": ".usage_api",
    }

    def __getattr__(name: str) -> object:
        if (module_name := _exports.get(name)) is None:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        value = getattr(import_module(module_name, __name__), name)
        globals()[name] = value
        return value

    def __dir__() -> list[str]:
        return sorted(globals().keys() | _exports.keys())
