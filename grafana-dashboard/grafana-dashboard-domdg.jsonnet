local lib = import 'grafana-dashboard-func.libsonnet';

local OnePanel(id, x, y, title, format, expr, legend) = [
   lib.Panel{
     id: id, x: x, y: y, 
     title: title, 
     format: format,
     expr: expr,
     legend: legend
   }
];

local ReadWritePanels(id, y, title, format, expr, legend) = [
   lib.Panel{
     id: id, x: 0, y: y, 
     title: title + " (Read)", 
     format: format,
     expr: std.strReplace(std.strReplace(expr, "LSOMIOTYPE", "Read"), "IOTYPE", "read"),
     legend: legend
   },
   lib.Panel{
     id: id + 1, x: 12, y: y, 
     title: title + " (Write)", 
     format: format,
     expr: std.strReplace(std.strReplace(expr,  "LSOMIOTYPE", "Write"), "IOTYPE", "write"),
     legend: legend
   },
];

local panels = 
  ReadWritePanels(10, 0, "DOM DG IOPS", "short", "sum(rate(vmware_vsan_domdg_io_total{disk_role=\"cache\",io_type=\"IOTYPE\",hostname=~\"$hostname\",cluster_name=~\"$Cluster\"}[1m])) by (hostname, disk_uuid,io_type)", "{{hostname}}") +
  ReadWritePanels(20, 8, "DOM DG Tput", "Bps", "sum(rate(vmware_vsan_domdg_io_bytes_total{disk_role=\"cache\",io_type=\"IOTYPE\",hostname=~\"$hostname\",cluster_name=~\"$Cluster\"}[1m])) by (hostname, disk_uuid,io_type)", "{{hostname}}") + 
  ReadWritePanels(30, 16, "DOM DG Avg IO Size", "bytes", "sum(rate(vmware_vsan_domdg_io_bytes_total{disk_role=\"cache\",io_type=\"IOTYPE\",hostname=~\"$hostname\",cluster_name=~\"$Cluster\"}[1m])) by (hostname, disk_uuid,io_type) / sum(rate(vmware_vsan_domdg_io_total{disk_role=\"cache\",io_type=\"IOTYPE\"}[1m]) +1) by (hostname, disk_uuid,io_type)", "{{hostname}}") +
  ReadWritePanels(40, 24, "DOM DG Latency", "s", "sum(rate(vmware_vsan_domdg_io_duration_seconds_total{disk_role=\"cache\",io_type=\"IOTYPE\",hostname=~\"$hostname\",cluster_name=~\"$Cluster\"}[1m])) by (hostname, disk_uuid,io_type) / sum(rate(vmware_vsan_domdg_io_total{disk_role=\"cache\",io_type=\"IOTYPE\"}[1m]) +1) by (hostname, disk_uuid,io_type)", "{{hostname}}") +
  ReadWritePanels(50, 32, "DOM DG Outstanding IO (QD)", "short", "sum(rate(vmware_vsan_domdg_numoio_total{disk_role=\"cache\",io_type=\"IOTYPE\",hostname=~\"$hostname\",cluster_name=~\"$Cluster\"}[1m])) by (hostname, disk_uuid,io_type) / sum(rate(vmware_vsan_domdg_io_total{disk_role=\"cache\",io_type=\"IOTYPE\"}[1m]) +1) by (hostname, disk_uuid,io_type)", "{{hostname}}") +
  OnePanel(60, 0, 40, "Write Buffer", "percentunit", "sum(vmware_vsan_disk_writebuffer_usage_bytes{disk_role=\"cache\",hostname=~\"$hostname\",cluster_name=~\"$Cluster\"}) by (hostname, disk_uuid) / sum(vmware_vsan_disk_writebuffer_size_bytes{disk_role=\"cache\"}) by (hostname, disk_uuid)", "{{hostname}}") +
  OnePanel(61, 12, 40, "WB Drain/Destage Rate", "Bps", "rate(vmware_vsan_disk_drain_bytes_total{disk_role=\"cache\",hostname=~\"$hostname\",cluster_name=~\"$Cluster\"}[1m])", "{{hostname}}, drain_type={{drain_type}}") +
  OnePanel(62, 0, 48, "Congestion (0-255)", "short", "sum(vmware_vsan_disk_congestion_total{disk_role=\"cache\",hostname=~\"$hostname\",cluster_name=~\"$Cluster\"}) by (hostname, disk_uuid, congestion_type)", "{{hostname}}, disk_role={{disk_role}}, disk_uuid={{disk_uuid}}") +
  OnePanel(63, 12, 48, "Congestion (Tput based)", "Bps", "sum(vmware_vsan_disk_congestion_bytespersecond{disk_role=\"cache\",hostname=~\"$hostname\",cluster_name=~\"$Cluster\"}) by (hostname, disk_uuid)", "{{hostname}}");


lib.Dashboard{
  title: "DOM DG", 
  uid: "vsan-domdg", 
  panels: panels,
  tags: ["vsan"]
}