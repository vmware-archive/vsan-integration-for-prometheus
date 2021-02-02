local lib = import 'grafana-dashboard-func.libsonnet';

local ReadWritePanels(id, y, title, format, expr) = [
   lib.Panel{
     id: id, x: 0, y: y, 
     title: title + " (Read)", 
     format: format,
     expr: std.strReplace(std.strReplace(expr, "LSOMIOTYPE", "read"), "IOTYPE", "read")
   },
   lib.Panel{
     id: id + 1, x: 12, y: y, 
     title: title + " (Write)", 
     format: format,
     expr: std.strReplace(std.strReplace(expr,  "LSOMIOTYPE", "write"), "IOTYPE", "write")
   },
];

local Panels(id, y, title, format, expr) = [
   lib.Panel{
     id: id, x: 0, y: y, 
     title: title, 
     format: format,
     expr: expr
   },
];

local ReadWriteLayersPanels(id, y, title, format, domexpr, domdgexpr,lsomcacheexpr) = 
  ReadWritePanels(id + 0, y +  0, "DOM Client " + title, format, std.strReplace(domexpr,  "ROLE", "client")) + 
  ReadWritePanels(id + 2, y +  8, "DOM Owner " + title, format, std.strReplace(domexpr,  "ROLE", "owner")) + 
  ReadWritePanels(id + 4, y + 16, "DOM Owner Leaf " + title, format, std.strReplace(domexpr,  "ROLE", "ownerLeaf")) +
  ReadWritePanels(id + 6, y + 24, "DOM CompMgr " + title, format, std.strReplace(domexpr,  "ROLE", "compmgr")) +
  ReadWritePanels(id + 8, y + 32, "DOM CompMgr DG " + title, format, domdgexpr) + 
  ReadWritePanels(id + 10, y + 40, "LSOM Cache " + title, format, std.strReplace(lsomcacheexpr, "DISKROLE", "cache")) +
  ReadWritePanels(id + 12, y + 48, "LSOM Capacity " + title, format, std.strReplace(lsomcacheexpr, "DISKROLE", "capacity")); 

local LayersPanels(id, y, title, format, expr) = 
  Panels(id + 0, y +  0, "DOM Client " + title, format, std.strReplace(expr,  "ROLE", "client")) + 
  Panels(id + 2, y +  8, "DOM Owner " + title, format, std.strReplace(expr,  "ROLE", "owner")) + 
  Panels(id + 4, y + 16, "DOM CompMgr " + title, format, std.strReplace(expr,  "ROLE", "compmgr")); 

local step = 56;
local panels = 
  ReadWriteLayersPanels(10, step * 0, "Latency", "s", 
    "sum(rate(vmware_vsan_dom_io_duration_seconds_total{role=\"ROLE\", io_type=\"IOTYPE\"}[1m])) by (hostname, io_type, role) / sum(rate(vmware_vsan_dom_io_total{role=\"ROLE\", io_type=\"IOTYPE\"}[1m]) +1) by (hostname, io_type, role)",
    "sum(rate(vmware_vsan_domdg_io_duration_seconds_total{disk_role=\"cache\",io_type=\"IOTYPE\"}[1m])) by (hostname, disk_uuid, io_type) / sum(rate(vmware_vsan_domdg_io_total{disk_role=\"cache\", io_type=\"IOTYPE\"}[1m]) +1) by (hostname, disk_uuid, io_type)",
    "sum(rate(vmware_vsan_disks_dev_duration_seconds_total{disk_role=\"DISKROLE\",io_type=\"LSOMIOTYPE\"}[1m])) by (hostname, disk_uuid, io_type) / sum(rate(vmware_vsan_disks_dev_io_total{disk_role=\"DISKROLE\", io_type=\"LSOMIOTYPE\"}[1m]) +1) by (hostname, disk_uuid, io_type)") +
  ReadWriteLayersPanels(30, step * 1, "IOPS", "short", 
    "sum(rate(vmware_vsan_dom_io_total{role=\"ROLE\", io_type=\"IOTYPE\"}[1m])) by (hostname, io_type, role)",
    "sum(rate(vmware_vsan_domdg_io_total{disk_role=\"cache\",io_type=\"IOTYPE\"}[1m])) by (hostname, disk_uuid, io_type)",
    "sum(rate(vmware_vsan_disks_dev_io_total{disk_role=\"DISKROLE\",io_type=\"LSOMIOTYPE\"}[1m])) by (hostname, disk_uuid, io_type)") +
  ReadWriteLayersPanels(50, step * 2, "Tput", "Bps", 
    "sum(rate(vmware_vsan_dom_io_bytes_total{role=\"ROLE\", io_type=\"IOTYPE\"}[1m])) by (hostname, io_type, role)",
    "sum(rate(vmware_vsan_domdg_io_bytes_total{disk_role=\"cache\",io_type=\"IOTYPE\"}[1m])) by (hostname, disk_uuid, io_type)",
    "sum(rate(vmware_vsan_disks_dev_bytes_total{disk_role=\"DISKROLE\",io_type=\"LSOMIOTYPE\"}[1m])) by (hostname, disk_uuid, io_type)") +
  LayersPanels(70, step * 3, "OIO", "short", 
    "sum(rate(vmware_vsan_dom_numoio_total{role=\"ROLE\"}[1m])) by (hostname, role) / sum(rate(vmware_vsan_dom_io_total{role=\"ROLE\"}[1m]) +1) by (hostname, role)");

   # XXX: Add all the missing ones

lib.Dashboard{
  title: "vSAN Layers", 
  uid: "vsan-layers", 
  panels: panels,
  tags: ["vsan"]
}

