# unifi_lte_stats.py

The script will collect data from a unifi controller (udm/udr) that has a U-LTE-Pro
with connected to it. It will read the stats from the controller device api. It will 
look for the device type "ULTEPEU" or "ULTEUS" and pushes the data in a prometheus
format to collection by the prometheus data collector.

I've included a ![grafana basic dashboard}(https://github.com/brendanbank/unifi_lte_collector/blob/535634d53950fa61d90f18b3e08fb6e615d0eaff/dashboard.json) to visualize the data.

![Grafana Dashboard](https://github.com/brendanbank/unifi_lte_collector/blob/d501a64103d3b8955e968e930b99d7b57abf2463/dashboard.png)



## configuration
The script will look for the authentication credentials in a "**.env**" file in the directory where
the script is placed.


You can configure the following variables.

	HOSTNAME=<the hostname of the collector>
	USERNAME=<username> # Make sure you create a read only user on the collector for this purpose.
	PASSWORD=<password> 

Optional variables:

	PORT=port that the prometheus client webserver is listening on, default is 9013
	FREQ=polling frequency, default is 30 (seconds)

The output of the command line interface command "curl localhost:9013" should look something
like below that can be polled by prometheus.


	brendan@srv: curl localhost:9013
	
	# HELP unifi_lte_info LTE info
	# TYPE unifi_lte_info gauge	unifi_lte_info{_id="<blanked>",ip="<blanked>",license_state="registered",lte_band="eutran-1",lte_cell_id="<blanked>",
	lte_connected="yes",lte_iccid="<blanked>",lte_imei="<blanked>",lte_ip="<blanked>",lte_mode="LTE",lte_networkoperator="<blanked>",
	lte_pdptype="IPV4",lte_radio="home",lte_radio_mode="LTE",lte_rat="LTE",lte_signal="Good signal strength (3)",mac="<blanked>",
	model="ULTEPEU",name="U-LTE-Pro",version="6.2.52.14128"} 1.0
	# HELP unifi_lte_rx_chan lte_rx_chan
	# TYPE unifi_lte_rx_chan gauge
	unifi_lte_rx_chan{id="<blanked>",model="ULTEPEU",name="U-LTE-Pro"} 125.0
	# HELP unifi_lte_tx_chan lte_tx_chan
	# TYPE unifi_lte_tx_chan gauge
	unifi_lte_tx_chan{id="<blanked>",model="ULTEPEU",name="U-LTE-Pro"} 18125.0
	# HELP unifi_lte_rssi lte_rssi
	# TYPE unifi_lte_rssi gauge
	unifi_lte_rssi{id="<blanked>",model="ULTEPEU",name="U-LTE-Pro"} -75.0
	# HELP unifi_lte_rsrq lte_rsrq
	# TYPE unifi_lte_rsrq gauge
	unifi_lte_rsrq{id="<blanked>",model="ULTEPEU",name="U-LTE-Pro"} -11.0
	# HELP unifi_lte_rsrp lte_rsrp
	# TYPE unifi_lte_rsrp gauge
	unifi_lte_rsrp{id="<blanked>",model="ULTEPEU",name="U-LTE-Pro"} -103.0
	# HELP unifi_total_tx_bytes total_tx_bytes
	# TYPE unifi_total_tx_bytes gauge
	unifi_total_tx_bytes{id="<blanked>",model="ULTEPEU",name="U-LTE-Pro"} 4.6432748e+07
	# HELP unifi_total_rx_bytes total_rx_bytes
	# TYPE unifi_total_rx_bytes gauge
	unifi_total_rx_bytes{id="<blanked>",model="ULTEPEU",name="U-LTE-Pro"} 3.2299633e+07

