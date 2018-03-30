// source 1: https://bost.ocks.org/mike/path/
// source 2: https://github.com/shanealynn/async_flask
$(document).ready( function hello() {
        var socket_url = 'http://' + document.domain + ':8081' + '/test1'
        console.log(socket_url)
        var socket = io.connect(socket_url);
        var socket_number = 0;

        var history = 5 * 60 * 1000, // 5 minutes
            duration = 250,
            now = new Date()
            data = [
                {'date': now - 2, 'reading': 0},
                {'date': now - 1, 'reading': 0},
            ]

        var svg = d3.select("#graph_1"),
            margin = {top: 50, right: 0, bottom: 20, left: 40},
            width = +svg.attr("width") - margin.right,
            height = +svg.attr("height") - margin.top - margin.bottom;

        var x = d3.scaleTime()
            .range([0, width]);

        var y = d3.scaleLinear()
            .range([height, 0]);

        x.domain(d3.extent(data, function(d) { return d.date; }));
        y.domain([0, d3.max(data, function(d) { return d.reading; })*1.2]);

        var line = d3.line()
            .x(function(d) { return x(d.date); })
            .y(function(d) { return y(d.reading); });


        var margin = {top: 20, right: 20, bottom: 20, left: 40},
            width = +svg.attr("width") - margin.left - margin.right,
            height = +svg.attr("height") - margin.top - margin.bottom,
            g = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        g.append("defs").append("clipPath")
            .attr("id", "clip")
          .append("rect")
            .attr("width", width)
            .attr("height", height);

        var x_axis = g.append("g")
            .attr("class", "axis axis--x")
            .attr("transform", "translate(0," + y(0) + ")")
            .call(d3.axisBottom(x))

        var y_axis = g.append("g")
            .attr("class", "axis axis--y")
            .call(d3.axisLeft(y));
            ;

        var path = g.append("g")
                .attr("clip-path", "url(#clip)")
            .append("path")
                .datum(data)
                .attr("fill", "none")
                .attr("stroke", "steelblue")
                .attr("stroke-linejoin", "round")
                .attr("stroke-linecap", "round")
                .attr("stroke-width", 2.5)
                .attr("d", line)
            .transition()
                .duration(duration)
                .ease(d3.easeLinear)
                .on("start", tick);

        function update_data() {
             // update the domains
            now = (new Date()).getTime();
            data.push({'date': now, 'reading': socket_number});

            min_time = d3.min(data, function(d) { return d.date; })
            max_time = d3.max(data, function(d) { return d.date; }) + 15*1000
            x.domain([min_time, max_time]);
            y.domain([0, d3.max(data, function(d) { return d.reading; })*1.2]);

            // pop the oldest data point
            if (now - data[0].date >= history) {
                data.shift();
            }
        }

        function tick() {
            update_data()

            // redraw the line
            d3.select(this)
              .attr("d", line)
              .attr("transform", null);

            // update the axes
            x_axis.call(d3.axisBottom(x))
            y_axis.call(d3.axisLeft(y))

            // slide the line left
            d3.active(this)
                .attr("transform", "translate(" + x(data[0].date - 1) + ")")
                .transition()
                  .on("start", tick);
        };

        //receive details from server
        socket.on('newnumber', function(msg) {
            // console.log(msg)
            console.log(new Date())
            console.log('New socket msg received: ' + msg.number)
            socket_number = msg.number;
            update_data()
        });

        // $(window).blur(function(e) {
        //     // Do Blur Actions Here

        // });
        // $(window).focus(function(e) {
        //     // Do Focus Actions Here
        // });
});

