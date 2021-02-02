# vSAN Grafana Dashboards

## Dashboards

Use the dashboards as entry points for debugging, but often it is useful to click on a panel,
select `Explore` and reefine the query to learn more. For example, if the panel shows IOPS
broken out by disk group, it may be useful to adjust the query to aggregate to host or even
cluster level.

### Layers

This dashboard focusses on tracking one metric across all the vSAN layers, e.g. latency from
DOM Client, to DOM Owner, to DOM Owner Leaf, to DOM Comp Mgr (host), to DOM Comp Mgr (per DG),
to LSOM Cache (per DG), to LSOM Capacity (per capacity disk).

After covering all layers for latency, it also covers the same for IOPS, Tput and Outstanding IO.

Here is a screenshot of [vSAN layer dashboard](../screenshots/grafana-vsan-layers.png).

### DOM DiskGroup

This dashboard focusses on the DOM Disk Group layer, a good way to look at the load of all
the Disk Groups, including the scheduler in front of them. The focus lies on showing all relevant
metrics: IOPS, Tput, Latency, Outstanding IO, etc.

Here is a screenshot of [vSAN DOM diskgroup dashboard](../screenshots/grafana-dom-dg.png).

### CPU

This dashboard looks at the vSAN CPU consumption and for each subsystem of vSAN shows the top-5
consumers of CPU. For most items 100% is the maximum consumption at which a bottleneck is 
reached.

Here is a screenshot of [vSAN CPU dashboard](../screenshots/grafana-vsan-cpu.png).

## How to build

In this directory we define our dashboards using `jsonnet`, a JSON templating language, because
dashboards follow a pretty consistent structure and we want an easy way to build dashboards that
show similar metrics across different IO types (read/write), layers (DOM Client, DOM Owner, DOM
CompMgr, LSOM) or metric type (latency, IOPS, Tput), etc. 

But we also want to make it easy for our users, and so we don't want to require them to have
jsonnet installed and so we check in both the final JSON as well as the jsonnet files.

We tested with jsonnet `v0.13.0`, installed via `brew`, available in the `$PATH`. 
```bashbash 
cd /path/to/vsan-prometheus-repo
bash grafana-dashboard/build.sh
```

