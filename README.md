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

## Example Load Test
- You can refer to the test `test_example.py` in the `example` directory for a basic 
  skeleton of how to get a load test running. In the same directory, there is also an 
  example `conftest.py` that will show you how to get basic parameterization working.
- This test can be invoked by running `pytest example/test_example.py` in the root of 
  this project.
- This test can also be invoked via a YAML scenario file:
```shell
cd example
pytest example_scenarios.YAML --tags=example1
```
 In this example scenario file, you can see how grasshopper_args, 
 grasshopper_scenario_args, and tags are being set.
<p align="right">(<a href="#top">back to top</a>)</p>

## Creating a load test
When creating a new load test, the primary grasshopper function you will be using 
is called `Grasshopper.launch_test`. This function can be imported like so: `from grasshopper.lib.grasshopper import Grasshopper`
`launch_test` takes in a wide variety of args:
- `user_classes`: User classes that the runner will run. These user classes must 
  extend BaseJourney, which is a grasshopper class 
  (`from grasshopper.lib.journeys.base_journey import BaseJourney`). This can be a 
  single class, a list of classes, or a dictionary where the key is the class and 
  the value is the locust weight to assign to that class.
- `**complete_configuration`: In order for the test to have the correct configuration, you 
  must pass in the kwargs provided by the `complete_configuration` fixture. See example 
  load test on how to do this properly.
<p align="right">(<a href="#top">back to top</a>)</p>

## Scenario Args   

- If you want to parameterize your journey class, you should use the `scenario_args` 
  dict. This is the proper way to pass in values from outside of 
  the journey for access by the journey code. Note that each journey gets a 
  ***copy*** on start, so the journey itself can safely modify its own dictionary 
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
def test_run_example_journey(complete_configuration):
    # update scenario args before initialization
    ExampleJourney.update_incoming_scenario_args(complete_configuration)
    
    # launch the journey
    locust_env = Grasshopper.launch_test(ExampleJourney, **complete_configuration)
    return locust_env
```
<p align="right">(<a href="#top">back to top</a>)</p>

## Commonly used grasshopper pytest arguments
- `--runtime`: Number of seconds to run each test. Set to 120 by default.
- `--users`: Max number of users that are spawned. Set to 1 by default.
- `--spawn_rate` : Number of users to spawn per second. Set to 1 by default.
- `--shape`: The name of a shape to run for the test. 
If you don't specify a shape or shape instance, then the shape `Default` will be used, 
  which just runs with the users, runtime & spawn_rate specified on the command line (or picks up defaults 
of 1, 1, 120s). See `utils/shapes.py` for available shapes and information on how to add
your own shapes.
- `--scenario_file` If you want a yaml file where you pre-define some args, this is how 
you specify that file path. For example, 
  `scenario_file=example/scenario_example.YAML`. 
- `--scenario_name` If `--scenario_file` was specified, this is the scenario name that is 
within that YAML file that corresponds to the scenario you wish to run. Defaults to None.
- `--tags` See below example: `Loop through a collection of scenarios that match some 
  tag`.
- `--scenario_delay` Adds a delay in seconds between scenarios. Defaults to 0.
- `--influx_host` If you want to report your performance test metrics to some influxdb, 
you must specify a host.
    E.g. `1.1.1.1`. Defaults to None.
- `--influx_port`: Port for your `influx_host` in the case where it is non-default.
- `--influx_user`: Username for your `influx_host`, if you have one.
- `--influx_pwd`: Password for your `influx_host`, if you have one.

<p align="right">(<a href="#top">back to top</a>)</p>

## Launching tests with a configuration
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

<p align="right">(<a href="#top">back to top</a>)</p>

## Configuring Grasshopper
<a id="creating"></a>

Grasshopper adds a variety of parameters relating to performance testing along with a
variety of ways to set these values.

Recent changes (>= 1.1.1) include an expanded set of sources, almost full access to all 
arguments via every source (some exceptions outlined below), and the addition of some 
new values that will be used with integrations such as report portal & slack 
(integrations are NYI). These changes are made in a backwards compatible manner, 
meaning all existing grasshopper tests should still run without modification. The 
original fixtures and sources for configuration are deprecated, but still produce the 
same behavior.

All of the usual [pytest arguments](https://docs.pytest.org/en/6.2.x/usage.html) also remain available.

The rest of the sections on configuration assume you are using `locust-grasshopper>=1.1.1`.
<p align="right">(<a href="#top">back to top</a>)</p>

### Sources
Currently, there are 5 different sources for configuration values and they are, in 
precedence order 

+ command line arguments
+ environment variables
+ scenario values from a scenario yaml file
+ grasshopper configuration file
+ global defaults (currently stored in code, not configurable by consumers)

Obviously, the global defaults defined by Grasshopper are not really a source for
consumers to modify, but we mention it so values don't seem to appear "out of thin air".
<p align="right">(<a href="#top">back to top</a>)</p>

### Categories
The argument list is getting lengthy, so we've broken it down into categories. These
categories are entirely for humans: better readability, understanding and ease of use. 
Once they are all fully loaded by Grasshopper, they will be stored in a single 
`GHConfiguration` object (`dict`). By definition, every argument is in only one category
and there is no overlap of keys between the categories. If the same key is supplied in
multiple categories, they will be merged with the precedence order as they appear in
the table.

| Name        | Scope              | Description/Usage                                                                                                                                                                                                                                         |
|-------------| ------------------ |-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Grasshopper | Session            | Variables that rarely change, may span many test runs.                                                                                                                                                                                                    |
| Test Run    | Session            | Variables that may change per test run, but are the<br/>same for every scenario in the run                                                                                                                                                                |
| Scenario    | Session            | Variables that may change per scenario and are often<br/>scenario specific; Includes user defined variables that are<br/>not declared as command line arguments by Grasshopper.<br/>However, you may use pytest's addoptions hook in your <br/>conftest to define them. |

At least one of the sections must be present in the global configuration file and
eventually this will be the same in the configuration section of a scenario in a scenario 
yaml file. Categories are not used when specifying environment variables or command line
options. We recommend that you use these categories in file sources, but if a variable 
is in the wrong section, it won't actually affect the configuration loading process.
<p align="right">(<a href="#top">back to top</a>)</p>

### Using Configuration Values 
Your test(s) may access the complete merged set of key-value pairs via the session scoped 
fixture `complete_configuration`. This returns a `GHConfiguration` object (dict) which
is unique to the current scenario. This value will be re-calculated for each new scenario
executed.

A few perhaps not obvious notes about configuration:
+ use the environment variable convention of all uppercase key names (e.g. `RUNTIME=10`)
to _specify_ a key-value pair via an environment value
+ use the lower case key to _access_ a key from the `GHConfiguration` object 
(e.g. `x = complete_configuration("runtime")`) regardless of the original source(s)
+ use `--` before the key name to specify it on the command line (e.g. `--runtime=10`)
+ configure a grasshopper configuration file by creating a session scoped fixture loaded 
by your conftest.py called `grasshopper_config_file_path` which returns the full path to a 
configuration yaml file.
+ grasshopper supports thresholds specified as
  + a json string - required for environment variable or commandline, but also accepted
  from other sources
  + a dict - when passing in via the `scenario_args` method (more details on that below)
  or via a journey class's `defaults` attr.

```python
@pytest.fixture(scope="session")
def grasshopper_config_file_path():
    return "path/to/your/config/file"
```

An example grasshopper configuration file:
```yaml
grasshopper:
  influx_host: 1.1.1.1
test_run:
  users: 1.0
  spawn_rate: 1.0
  runtime: 600
scenario:
  key1 : 'value1'
  key2: 0
```
<p align="right">(<a href="#top">back to top</a>)</p>

### Additional Extensions to the configuration loading process

If you would like to include other environment variables that might be present in the
system, you can define a fixture called `extra_env_var_keys` which returns a list of key
names to load from the `os.environ`. Keys that are missing in the environment will not 
be included in the `GHConfiguration` object.

Any environment variables that use the prefix `GH_` will also be included in the 
`GHConfiguration` object. The `GH_` will be stripped before adding and any names that
become zero length after the strip will be discarded. This is a mechanism to include any
scenario arguments you might like to pass via an environment variable.

In the unlikely case that you need to use a different prefix to designate scenario
variables, you can define a fixture called `env_var_prefix_key` which returns a prefix
string. The same rules apply about which values are included in the configuration.

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
trend or a request response time. Thresholds default to the 0.9 percentile of timings. 
Here is an example of using a threshold: 

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
def test_run_example_journey(complete_configuration):
    ExampleJourney.update_incoming_scenario_args(complete_configuration)
    ExampleJourney.update_incoming_scenario_args({
        "thresholds": {
            "get google":
                {
                    "type": "get",
                    "limit": 4000  # 4 second HTTP response threshold
                },
            "my custom trend":
                {
                    "type": "custom",
                    "limit": 11000  # 11 second custom trend threshold
                }
        }
    })
    
    locust_env = Grasshopper.launch_test(ExampleJourney, **complete_configuration)
    return locust_env
```

Thresholds can also be defined for individual YAML scenarios. Refer to the `thresholds` 
key in `example/example_scenarios.YAML` for how to use thresholds for YAML scenarios.

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