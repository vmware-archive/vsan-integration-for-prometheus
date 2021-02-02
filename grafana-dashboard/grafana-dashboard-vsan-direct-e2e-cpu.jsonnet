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
  Panels(id + 0, y +  0, "PVSCSI " + title, format, std.strReplace(expr,  "QUERY", "name=~\"PVSCSI-.*\"")) +
  Panels(id + 2, y +  8, "VMHBA Compl " + title, format, std.strReplace(expr,  "QUERY", "name=~\"Cmpl-vmhba.*\"")) +
  Panels(id + 4, y + 16, "Cmd Compl " + title, format, std.strReplace(expr,  "QUERY", "name=~\"CmdCompl.*\"")) +
  Panels(id + 6, y + 24, "NVMe Compl " + title, format, std.strReplace(expr,  "QUERY", "name=~\"NVMeCompl.*\"")) +
  Panels(id + 8, y + 32, "vmx " + title, format, std.strReplace(expr,  "QUERY", "name=\"vmx\""));
local panels =
  [lib.Panel{
     id: 5, x: 0, y: 0,
     title: "Total Host Coreutil (percent)",
     format: "percent",
     expr: "sum(rate(vmware_host_cpu_seconds_total{type=\"coreutiltime\"}[1m])) by (hostname) / sum(rate(vmware_host_cpu_seconds_total{type=\"elapsedtime\"}[1m])) by (hostname) * 100"
   },
   lib.Panel{
     id: 6, x: 12, y: 0,
     title: "Total Host CPU Usedtime (percent)",
     format: "percent",
     expr: "sum(rate(vmware_host_cpu_seconds_total{type=\"usedtime\"}[1m])) by (hostname) / sum(rate(vmware_host_cpu_seconds_total{type=\"elapsedtime\"}[1m])) by (hostname) * 100"
   },
  ] +
  LayersPanels(10, 8, "Host CPU Utilization (Cores)", "short",
    "sum(rate(vmware_esx_world_USAGEtime_seconds_total{QUERY}[1m]) / rate(vmware_esx_world_uptime_seconds_total{QUERY}[1m])) by (hostname)");
   # XXX: Add all the missing ones
lib.Dashboard{
  title: "vSAN Direct e2e CPU",
  uid: "vsan-direct-e2e-cpu",
  panels: panels,
  tags: ["vsan"]
}
