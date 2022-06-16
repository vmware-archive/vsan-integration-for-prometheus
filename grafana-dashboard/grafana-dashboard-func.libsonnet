{
  "Panel": {
        local panel = self,
    "aliasColors": {},
    "bars": false,
    "dashLength": 10,
    "dashes": false,
    "datasource": null,
    "fill": 1,
    "fillGradient": 0,
    "gridPos": {
      "h": 8,
      "w": 12,
      "x": panel.x,
      "y": panel.y
    },
    "hiddenSeries": false,
    "id": panel.id,
    "legend": {
      "avg": false,
      "current": false,
      "max": false,
      "min": false,
      "show": true,
      "total": false,
      "values": false
    },
    "lines": true,
    "linewidth": 1,
    "nullPointMode": "null",
    "options": {
      "dataLinks": [],
      "displayMode": "list",
      "placement": "bottom",
    },
    "percentage": false,
    "pointradius": 2,
    "points": false,
    "renderer": "flot",
    "seriesOverrides": [],
    "spaceLength": 10,
    "stack": false,
    "steppedLine": false,
    "targets": [
      {
        "expr": panel.expr,
        "refId": "A",
        #"legendFormat": "{{hostname}}"
        "legendFormat": panel.legend
      }
    ],
    "thresholds": [],
    "timeFrom": null,
    "timeRegions": [],
    "timeShift": null,
    "title": panel.title,
    "tooltip": {
      "shared": true,
      "sort": 0,
      "value_type": "individual"
    },
    "type": "timeseries",
    "xaxis": {
      "buckets": null,
      "mode": "time",
      "name": null,
      "show": true,
      "values": []
    },
    "yaxes": [
      {
        "format": panel.format,
        "label": "",
        "logBase": 1,
        "max": null,
        "min": null,
        "show": true
      },
      {
        "format": "short",
        "label": null,
        "logBase": 1,
        "max": null,
        "min": null,
        "show": true
      }
    ],
    "yaxis": {
      "align": false,
      "alignLevel": null
    }
  },
  "Dashboard": {
        local dash = self,
    "annotations": {
      "list": [
        {
          "builtIn": 1,
          "datasource": "-- Grafana --",
          "enable": true,
          "hide": true,
          "iconColor": "rgba(0, 211, 255, 1)",
          "name": "Annotations & Alerts",
          "type": "dashboard"
        }
      ]
    },
    "editable": true,
    "gnetId": null,
    "graphTooltip": 0,
    "id": 1,
    "links": [],
    "panels": dash.panels,
    "refresh": false,
    "schemaVersion": 22,
    "style": "dark",
    "tags": [],
    "templating": {
      "list": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "MKCZcgjnz"
          },
          "definition": "label_values(cluster_name)",
          "hide": 0,
          "includeAll": false,
          "multi": false,
          "name": "Cluster",
          "options": [],
          "query": {
            "query": "label_values(cluster_name)",
            "refId": "StandardVariableQuery"
          },
          "refresh": 1,
          "regex": "",
          "skipUrlSync": false,
          "sort": 1,
          "type": "query"
        },
        {
          "datasource": {
            "type": "prometheus",
            "uid": "MKCZcgjnz"
          },
          "definition": "label_values({cluster_name=~\"$Cluster\"},hostname)",
          "hide": 0,
          "includeAll": true,
          "multi": true,
          "name": "hostname",
          "options": [],
          "query": {
            "query": "label_values({cluster_name=~\"$Cluster\"},hostname)",
            "refId": "StandardVariableQuery"
          },
          "refresh": 1,
          "regex": "",
          "skipUrlSync": false,
          "sort": 1,
          "type": "query"
        }
      ]
    },
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "timepicker": {
      "refresh_intervals": [
        "5s",
        "10s",
        "30s",
        "1m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "1d"
      ]
    },
    "timezone": "",
    "title": dash.title,
    "uid": dash.uid,
    "version": 2
  }
}