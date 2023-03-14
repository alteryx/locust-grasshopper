<div id="top"></div>

# Grasshopper

A lightweight framework for performing load tests against an environment, primarily 
against an API. Grasshopper glues [Locust](https://locust.io/), [Pytest](https://docs.pytest.org/en/7.1.x/#), some plugins (namely [Locust InfluxDBListener](https://github.com/hoodoo-digital/locust-influxdb-listener) ) and some custom code to provide a
package that makes authoring load tests simple with very little boilerplate needed.

Here are some key functionalities that this project extends on Locust:
- [checks](#checks)
- [custom trends](#custom-trends)
- [timing thresholds](#thresholds)
- [streamlined metric reporting/tagging system](#db-reporting)
  (only influxDB is supported right now)

## Installation
This package can be installed via pip: `pip install locust-grasshopper`



## Supported pytest arguments
<a id="creating"></a>
After installing grasshopper, you should automatically be given access to a variety 
of pytest params:
- `--runtime`: Number of seconds to run each test. Set to 120 by default.
- `--users`: Max number of users that are spawned. Set to 1 by default.
- `--spawn_rate` : Number of users to spawn per second. Set to 1 by default.
- `--shape`: The name of a shape to run for the test. 
If you don't specify a shape or shape instance, then the shape `Default` will be used, 
  which just runs with the users, runtime & spawn_rate specified on the command line (or picks up defaults 
of 1, 1, 120s). See `utils/shapes.py` for available shapes and information on how to add
your own shapes.
- `--scenario_file` If you want a yaml file where you pre-define some grasshopper 
  args or scenario args, this is how you specify that file path. For example, 
  `scenario_file=example/scenario_example.YAML`. This arg is currently 
  the only way to provide custom scenario args.
- `--scenario_name` If `--scenario_file` was specified, this is scenario name that is within that YAML file that corresponds to the scenario you wish to run. Defaults to None.
- `--tags` See below example: `Loop through a collection of scenarios that match some 
  tag`.
- `--scenario_delay` Adds a delay in seconds between scenarios. Defaults to 0.
- `--influxdb` If you want to report your performance test metrics to some influxdb, you must specify a host.
    E.g. `1.1.1.1`. Defaults to None.
- `--influx_port`: Port for your `influxdb` in the case where it is non-default.
- `--influx_user`: Username for your `influxdb`, if you have one.
- `--influx_pwd`: Password for your `influxdb`, if you have one.

All in all, there are a few ways you can actually collect and pass params to a test:
### Run a test with its defaults
`cd example`
`pytest test_example.py ...`

### Run a test with a specific scenario
`cd example`
`pytest test_example.py --scenario_file=example_scenarios.YAML --scenario_name=example_scenario_1 ...`

### Loop through a collection of scenarios that match some tag
`cd example`
`pytest example_scenarios.YAML --tags=smoke ...`

- As shown above, this case involves passing a `.YAML` scenario file into pytest instead of a `.py` file.
- The `--scenario_file` and `--scenario_name` args will be ignored in this case
- The `--tags` arg supports AND/OR operators according to the opensource `tag-matcher` package. More info on these operators can be found [here](https://pypi.org/project/tag-matcher/).
- If no `--tags` arg is specified, then ALL the scenarios in the `.yaml` file will be run.
- If a value is given for `--scenario_delay`, the test will wait that many seconds between collected scenarios.
- All scenarios are implicitly tagged with the scenario name to support easily selecting one single
scenario

**Creating a load test **
When creating a new load test, the primary grasshopper function you will be using 
is called `Grasshopper.launch_test`. This function can be imported like so: `from grasshopper.lib.grasshopper import Grasshopper`
`launch_test` takes in a wide variety of args:
- `user_classes`: User classes that the runner will run. These user classes must 
  extend BaseJourney, which is a grasshopper class 
  (`from grasshopper.lib.journeys.base_journey import BaseJourney`). This can be a 
  list of classes or just a single class.
- `**grasshopper_args`: In order for the test to have the correct configuration, you 
  must pass in the kwargs provided by the `grasshopper_args` fixture. See example 
  load test on how to do this properly.

<p align="right">(<a href="#top">back to top</a>)</p>

## Example Load Test  

- You can refer to the test `test_example.py` in the `example` directory for a basic 
  skeleton of how to get a load test running. In the same directory, there is also an 
  example `conftest.py` that will show you how to get basic parameterization working.
- This test can be invoked by running `pytest example/test_example.py` in the root of 
  this project.
- This test can also be invoked via a YAML scenario file: (`cd example`, `pytest 
  example_scenarios.YAML --tags=example1`). In this example scenario file, you can 
  see how grasshopper_args, grasshopper_scenario_args, and tags are being set.

<p align="right">(<a href="#top">back to top</a>)</p>

## Scenario Args   

- If you want to parameterize your journey class, you should use the `scenario_args` 
  dict. This is the proper way to pass in values from outside of 
  the journey for access by the journey code. Note that each journey gets a 
  ***copy*** on start, so the journey itself can safely modify it's own dictionary 
  once the test is running.
  `scenario_args` exists for any journey that extends the grasshopper `base_journey` 
  class. 
  `scenario_args` also grabs from `self.defaults` on initialization. For example:
```python
from locust import between, task
from grasshopper.lib.journeys.base_journey import BaseJourney
from grasshopper.lib.grasshopper import Grasshopper

# a journey class with an example task
class ExampleJourney(BaseJourney):
    # number of seconds to wait between each task
    wait_time = between(min_wait=20, max_wait=30)
    
    # this defaults dictionary will be merged into scenario_args with lower precedence 
    # when the journey is initialized
    defaults = {
        "foo": "bar",
    }
    
    @task
    def example_task:
        logging.info(f'foo is `{self.scenario_args.get("foo")}`.')
        
        # aggregate all metrics for the below request under the name "get google"
        # if name is not specified, then the full url will be the name of the metric
        response = self.client.get('https://google.com', name='get google')

# the pytest test which launches the journey class
def test_run_example_journey(grasshopper_scenario_args, grasshopper_args):
    # update scenario args before initialization
    ExampleJourney.update_incoming_scenario_args(grasshopper_scenario_args)
    
    # launch the journey
    locust_env = Grasshopper.launch_test(ExampleJourney, **grasshopper_args)
    return locust_env
```
<p align="right">(<a href="#top">back to top</a>)</p>

## Checks
<a id="checks"></a>
Checks are an assertion that is recorded as a metric. 
They are useful both to ensure your test is working correctly 
(e.g. are you getting a valid id back from some post that you sent) 
and to evaluate if the load is causing intermittent failures 
(e.g. sometimes a percentage of workflow runs don't complete correctly the load increases). 
At the end of the test, checks are aggregated by their name across all journeys that 
ran and then reported to the console. They are also forwarded to the DB 
in the "checks" table. Here is an example of using a check: 

```python
from grasshopper.lib.util.utils import check
...
response = self.client.get(
    'https://google.com', name='get google'
)
check(
    "get google responded with a 200",
    response.status_code == 200,
    env=self.environment,
)
```
It is worth noting that it is NOT necessary to add checks on the http codes. All the 
HTTP return codes are tracked automatically by grasshopper and will be sent to the DB. 
If you aren't using a DB then you might want the checks console output.
<p align="right">(<a href="#top">back to top</a>)</p>

## Custom Trends
<a id="custom-trends"></a>
Custom trends are useful when you want to time something that spans multiple HTTP 
calls. They are reported to the specified database just like any other HTTP request, 
but with the "CUSTOM" HTTP verb as opposed to "GET", "POST", etc. Here is an example 
of using a custom trend:
```python
from locust import between, task
from grasshopper.lib.util.utils import custom_trend
...

@task
@custom_trend("my_custom_trend")
def google_get_journey(self)
    for i in range(len(10)):
        response = self.client.get(
            'https://google.com', name='get google', context={'foo1':'bar1'}
        )
```
<p align="right">(<a href="#top">back to top</a>)</p>

## Thresholds
<a id="thresholds"></a>
Thresholds are time-based, and can be added to any trend, whether it be a custom 
trend or a request response time. Thresholds are currently based off of the 90th 
percentile of timings. Here is an example of using a threshold: 

```python
# a journey class with an example threshold
from locust import between, task
from grasshopper.lib.journeys.base_journey import BaseJourney
from grasshopper.lib.grasshopper import Grasshopper

class ExampleJourney(BaseJourney):
    # number of seconds to wait between each task
    wait_time = between(min_wait=20, max_wait=30)
    
    @task
    def example_task:
        self.client.get("https://google.com", name="get google")
        
    @task
    @custom_trend("my custom trend")
    def example_task_custom_trend:
        time.sleep(10)

# the pytest test which launches the journey class, thresholds could be 
# parameterized here as well.
def test_run_example_journey(grasshopper_scenario_args, grasshopper_args):
    ExampleJourney.update_incoming_scenario_args(grasshopper_scenario_args)
    ExampleJourney.update_incoming_scenario_args({
        "thresholds": {
            "{GET}get google": 4000, # 4 second HTTP response threshold
            "{CUSTOM}my custom trend": 11000 # 11 second custom trend threshold
            }
        }) 
    
    locust_env = Grasshopper.launch_test(ExampleJourney, **grasshopper_args)
    return locust_env
```

After a test has concluded, trend/threshold data can be found in 
`locust_env.stats.trends`. 
This data is also reported to the console at the end of each test.

<p align="right">(<a href="#top">back to top</a>)</p>

## Time Series DB Reporting and Tagging
<a id="db-reporting"></a>
When you specify a time series database URL param to `launch_test`, such as 
`influx_host`, all metrics will be automatically reported to tables within the `locust` 
timeseries database via the specified URL. These tables include:
- `locust_checks`: check name, check passed, etc.
- `locust_events`: test started, test stopped, etc.
- `locust_exceptions`: error messages
- `locust_requests`: HTTP requests and custom trends

An example grafana dashboard which queries these tables can be found in 
`example/grafana_dashboards`

There are a few ways you can pass in extra tags which 
will be reported to the time series DB:

1. **HTTP Request Tagging**   
     All HTTP requests are automatically tagged with their name. If you want to pass in 
     extra tags for a particular HTTP request, you can pass them in 
     as a dictionary for the `context` param when making a request. For example:

    ```python
    self.client.get('https://google.com', name='get google', context={'foo':'bar'})
    ```
    The tags on this metric would then be: `{'name': 'get google', 'foo': 'bar'}` which 
    would get forwarded to the database if specified. 

2. **Check Tagging**   
   When defining a check, you can pass in extra tags with the `tags` parameter:
    ```python
    from grasshopper.lib.util.utils import check
    ...
    response = self.client.get(
    'https://google.com', name='get google', context={'foo1':'bar1'}
    )
    check(
       "get google responded with a 200",
       response.status_code == 200,
       env=self.environment,
       tags = {'foo2': 'bar2'}
    )
    ```

3. **Custom Trend Tagging**   
    Since custom trends are decorators, they do not have access to 
   non-static class variables when defined. Therefore, you must use the 
   `extra_tag_keys` param, which is an array of keys that exist in the journey's 
   scenario_args. So for example, if a journey had the scenario args `{"foo" : "bar"}` and you wanted to tag 
   a custom trend based on the "foo" scenario arg key, you would do something like this:
    ```python
    from locust import between, task
    from grasshopper.lib.util.utils import custom_trend
    ...
        
    @task
    @custom_trend("my_custom_trend", extra_tag_keys=["foo"])
    def google_get_journey(self)
       for i in range(len(10)):
          response = self.client.get(
             'https://google.com', name='get google', context={'foo1':'bar1'}
          )
    ```
<p align="right">(<a href="#top">back to top</a>)</p>

## Project Roadmap

- [X] Custom Trends
- [X] Checks
- [X] Thresholds
- [X] Tagging
- [X] InfluxDB metric reporting
- [ ] PrometheusDB metric reporting
- [ ] Slack reporting
- [ ] ReportPortal reporting

See the open issues for a full list of proposed features (and known issues).

<p align="right">(<a href="#top">back to top</a>)</p>

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Make sure unit tests pass (`pytest tests/unit`)
4. Add unit tests to keep coverage up, if necessary
5. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
6. Push to the Branch (`git push origin feature/AmazingFeature`)
7. Open a Pull Request

<p align="right">(<a href="#top">back to top</a>)</p>