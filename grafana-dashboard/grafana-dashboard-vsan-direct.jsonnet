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

local ReadWriteLayersPanels(id, y, title, format, vsandirectexpr) =
  ReadWritePanels(id + 12, y + 48, "vSAN Direct " + title, format, vsandirectexpr);

local step = 56;
local panels =
  ReadWriteLayersPanels(10, step * 0, "Latency", "s",
    "sum(rate(vmware_vsan_disks_dev_duration_seconds_total{storagepool=~\"storagepool-vsandirect.*\",io_type=\"LSOMIOTYPE\"}[1m])) by (hostname, storagepool, io_type) / sum(rate(vmware_vsan_disks_dev_io_total{storagepool=~\"storagepool-vsandirect.*\", io_type=\"LSOMIOTYPE\"}[1m])) by (hostname, storagepool, io_type)") +
  ReadWriteLayersPanels(30, step * 1, "IOPS", "short",
    "sum(rate(vmware_vsan_disks_dev_io_total{storagepool=~\"storagepool-vsandirect.*\",io_type=\"LSOMIOTYPE\"}[1m])) by (hostname, storagepool, io_type)") +
  ReadWriteLayersPanels(50, step * 2, "Tput", "Bps",
    "sum(rate(vmware_vsan_disks_dev_bytes_total{storagepool=~\"storagepool-vsandirect.*\",io_type=\"LSOMIOTYPE\"}[1m])) by (hostname, storagepool, io_type)"
);

   # XXX: Add all the missing ones

lib.Dashboard{
  title: "vSAN Direct Disk",
  uid: "vsan-direct-layer",
  panels: panels,
  tags: ["vsan", "vsan70u1"]
}
