'use strict';
document.addEventListener('DOMContentLoaded', function () {
  setTimeout(function () {
    floatchart();
  }, 500);
});

var chart_users_month, chart_users_year, chart_visitors_month, chart_visitors_year, chart_user_agents, chart_operating_systems, chart_traffic;

function floatchart() {

  var options_monthly_chart = {
    series: [        
    ],
    chart: {
      type: 'bar',
      width: 300,
      height: 90,
      sparkline: {
        enabled: true
      }
    },
    dataLabels: {
      enabled: false
    },
    colors: ['#FFF'],
    plotOptions: {
      bar: {
        columnWidth: '80%'
      }
    },
    xaxis: {
      // crosshairs: {
      //   width: 2
      // },
      type: 'category',
      // categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    },      
    tooltip: {
      theme: 'dark',
      fixed: {
        enabled: false
      },
      x: {
        show: true
      },
      y: {
        title: {
          formatter: function (seriesName) {
            return 'Count: ';
          }
        }
      },
      marker: {
        show: false
      }
    }      
  };

  var options_yearly_chart = {
    series: [        
    ],
    chart: {
      type: 'bar',
      width: 300,
      height: 90,
      sparkline: {
        enabled: true
      }
    },
    dataLabels: {
      enabled: false
    },
    colors: ['#FFF'],
    plotOptions: {
      bar: {
        columnWidth: '80%'
      }
    },
    xaxis: {
      // crosshairs: {
      //   width: 2
      // },
      type: 'category',
      // categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    },
    // grid: {
    //   strokeDashArray: 4
    // },
    tooltip: {
      theme: 'dark',
      fixed: {
        enabled: false
      },
      x: {
        show: true
      },
      y: {
        title: {
          formatter: function (seriesName) {
            return 'Count: ';
          }
        }
      },
      marker: {
        show: false
      }
    }      
  };

  var options_pie_chart = {    
    chart: {
      width: 100,
      type: 'pie',
    },
    series: [],
    labels: [],
    plotOptions: {
      pie: {
        // customScale: 0.5,
        expandOnClick: true
      }
    },  
    legend: {
      show: false,
    },
    dataLabels: {
      enabled: false,
    },   
    // responsive: [{
    //   breakpoint: 480,
    //   options: {
    //     chart: {
    //       width: 200
    //     },
    //     legend: {
    //       position: 'bottom'
    //     }
    //   }
    // }]
  };

    
  // current month registered users daily summary
  (function () {    
    chart_users_month = new ApexCharts(document.querySelector("#tab-chart-users-month"), options_monthly_chart);
    chart_users_month.render();
  })();

  // current year registered users monthly summary
  (function () {    
    chart_users_year = new ApexCharts(document.querySelector("#tab-chart-users-year"), options_yearly_chart);
    chart_users_year.render();
  })();

  // current month visitors daily summary
  (function () {    
    chart_visitors_month = new ApexCharts(document.querySelector("#tab-chart-visitors-month"), options_monthly_chart);
    chart_visitors_month.render();
  })();

  // current year visitors monthly summary
  (function () {    
    chart_visitors_year = new ApexCharts(document.querySelector("#tab-chart-visitors-year"), options_yearly_chart);
    chart_visitors_year.render();
  })();

  // current year visitors user agents yearly summary
  (function () {    
    chart_user_agents = new ApexCharts(document.querySelector("#tab-chart-user-agents"), options_pie_chart);
    chart_user_agents.render();
  })();

  // current year visitors operating systems yearly summary
  (function () {    
    chart_operating_systems = new ApexCharts(document.querySelector("#tab-chart-operating-systems"), options_pie_chart);
    chart_operating_systems.render();
  })();

  // current year traffic
  (function () {
    var options = {
      chart: {
        type: 'bar',
        height: 480,
        stacked: true,
        toolbar: {
          show: false
        }
      },
      plotOptions: {
        bar: {
          horizontal: false,
          columnWidth: '50%'
        }
      },
      dataLabels: {
        enabled: false
      },
      colors: ['#673ab7', '#2196f3'],
      series: [],
      responsive: [
        {
          breakpoint: 480,
          options: {
            legend: {
              position: 'bottom',
              offsetX: -10,
              offsetY: 0
            }
          }
        }
      ],
      xaxis: {
        type: 'category',
        categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
      },
      grid: {
        strokeDashArray: 4
      },
      tooltip: {
        theme: 'dark'
      }
    };
    chart_traffic = new ApexCharts(document.querySelector('#tab-chart-traffic'), options);
    chart_traffic.render();
  })();
  
}
