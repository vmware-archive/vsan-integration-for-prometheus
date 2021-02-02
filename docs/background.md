# Background
## Prometheus

Prometheus is a powerful stats processing engine. It sucks in stats from any source that abides by a simple HTTP format.
That said, prometheus is opinionated to deliver a superior query engine:
* Metrics need to be named with a clear indication of:
* The unit (e.g. "seconds" or "bytes")
* The nature of the metric (e.g. point in time, or sum total over all time)
* If the same metric is collected in many places, the same metric name needs to be used
* Labels are then used to attribute, e.g. on which host the metric originated, or which subsystem generated it (e.g. LSOM vs. DOM Client vs. DOM Owner, etc.)
* TYPE and HELP information needs to be provided by metrics
* Should include information on where exactly the stat came from
* A good explanation for someone not intimitely familar with the system being monitored

As much as possible, prometheus wants "sum total over all time" values, not pre-computed averages. This allows Prometheus to be in
charge of the interval and computing the averages or any other values.

## Grafana

Grafana can use Prometheus as a backend "data store". Panels in dashboards can be
authored using queries, and templating can be used against labels. That said,
Grafana is mainly a tool for dashboards, i.e. panels someone authored that get
looked at again and again. But this isn't where prometheus shines. The power
of prometheus comes from the rich query language that can used in ad-hoc investigations.
Prometheus has a built-in UI to author ad-hoc queries, and even graph them, but this
UI isn't very good. 

In the latest TOT version (on master branch) of Grafana there is a new Explore UI
that allows much better ad-hoc query authoring. it is still in development, but
enabled in the prometheus.yaml file in this repo.

# Example queries:

* `sum(rate(vmware_vsan_dom_io_bytes_total{role="client"}[30s])) by (hostname) / 1024^2`
* `sum(rate(vmware_vsan_dom_io_bytes_total{role="client"}[5m])) by (hostname) / 1024^2`
* `sum(rate(vmware_vsan_dom_io_bytes_total{role="compmgr"}[30s])) by (hostname) / 1024^2`
* `sum(rate(vmware_vsan_dom_io_bytes_total{role="client",io_type="write"}[30s])) by (hostname) / 1024^2`
* `(sum(rate(vmware_vsan_dom_latency_seconds_total{role="client"}[5m])) by (hostname) / sum(rate(vmware_vsan_dom_io_total{role="client"}[5m])) by (hostname)) * 1000`