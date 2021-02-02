local lib = import 'grafana-dashboard-func.libsonnet';

local Panels(id, y, title, format, expr) = [
   lib.Panel{
     id: id, x: 0, y: y, 
     title: title + " (Usage)", 
     format: format,
     expr: std.strReplace(expr, "USAGE", "used")
   },
   lib.Panel{
     id: id + 1, x: 12, y: y, 
     title: title + " (Ready)", 
     format: format,
     expr: std.strReplace(expr, "USAGE", "ready")
   },
];

local LayersPanels(id, y, title, format, expr) = 
  Panels(id + 0, y +  0, "DOM " + title, format, std.strReplace(expr,  "SUBSYS", "DOM")) + 
  Panels(id + 2, y +  8, "LLOG " + title, format, std.strReplace(expr,  "SUBSYS", "LLOG")) + 
  Panels(id + 4, y + 16, "PLOG " + title, format, std.strReplace(expr,  "SUBSYS", "PLOG")) + 
  Panels(id + 6, y + 24, "Network " + title, format, std.strReplace(expr,  "SUBSYS", "Network")) + 
  Panels(id + 8, y + 32, "CMMDS " + title, format, std.strReplace(expr,  "SUBSYS", "CMMDS"));

local panels = 
  LayersPanels(10, 0, "Top-5 CPU Utilization", "percent", 
    "topk(5, rate(vmware_esx_world_USAGEtime_seconds_total{subsystem=\"SUBSYS\"}[1m]) / rate(vmware_esx_world_uptime_seconds_total{subsystem=\"SUBSYS\"}[1m])) * 100");

   # XXX: Add all the missing ones

lib.Dashboard{
  title: "vSAN CPU", 
  uid: "vsan-cpu", 
  panels: panels,
  tags: ["vsan"]
}

# 