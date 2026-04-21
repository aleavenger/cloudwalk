FROM grafana/grafana:11.1.0

ARG GRAFANA_INFINITY_PLUGIN_VERSION=3.6.0
RUN grafana cli plugins install yesoreyeram-infinity-datasource "${GRAFANA_INFINITY_PLUGIN_VERSION}"
