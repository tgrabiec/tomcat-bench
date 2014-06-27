Tomcat performance testing
=========================

# Setting up

The testing evnironment needs to be checked out on the machine from which tests will be started:

```sh
git clone https://github.com/tgrabiec/tomcat-bench ~/src/tomcat-bench
```

Note that this does not have to be (and shoud not be) the machine on which tomcat or load driver will run.

On the machines which you intend to use for testing, put the following configuration in `~/.bashrc`:

```sh
# This is the location into which benchmark scripts will be rsync'ed to
export BENCH_BASE=$HOME/src/tomcat-bench

# This directory will hold images for test
export BENCH_IMAGE_REPO=$HOME/img

PATH=$PATH:$BENCH_BASE
```

# Test configuration

You need to create a configuration file by copying `configuration_template.py` and filling it in. You will pass
the path to your configuration file to various commands.

The host names used during test are specified there. There are two machines required for tomcat test:
 * tomcat host
 * load driver

# Image repository

Image which is tested needs to come from a repository, which lives on the tomcat host machine.

To publish an image execute the following command in the directory in which you checked out `osv.git`:

```sh
$ bench.py push myimage
```

# Making image

The process of building an image for tomcat tests is fully automated. To build and publish an image run `bench.py make-img`:

```sh
$ ./bench.py make-img --conf conf-cloudius.py --src /data/tgrabiec/src myimage
```

The command can be started on any machine. The image will be made on the tomcat host machine.

The path you pass to `--src` will be used as a checkout base for various repositories. The file passed to `--conf` is the path
to your test configuration file. Check `bench.py make-img -h` for more options.

Note that you can always build an image yourself and publish using `bench.py push`.

# Publishing a Linux guest image

TODO

# Performing a test

The test is started like this:

```sh
./bench.py run --conf conf-cloudius.py --image myimage
```

Checkout `bench.py run -h` for more options.

After the test completes, the test result will be persisted in `results/<id>/` directory and will be available
to reporting commands.

The serial console will be redirected during test to `${BENCH_BASE}/qemu.log` on the tomcat host machine. After test the log
is copied to the result directory.

Each test has a JSON file with attributes holding environment information, test parameters and results:

```sh
$ cat results/1403858522.98/properties.json 
{
    "bench.version": "f00507ec40b6bca91714757586d93338e51478ab", 
    "datetime": "2014.06.27 10:42:03", 
    "id": "1403858522.98", 
    "load_driver": {
        "uname": "Linux huginn.cloudious.local 3.14.7-200.fc20.x86_64 #1 SMP Wed Jun 11 22:38:05 UTC 2014 x86_64 x86_64 x86_64 GNU/Linux", 
        "hostname": "huginn.cloudious.local", 
        "cpu": {
            "n_cores": "8", 
            "model": " Intel(R) Core(TM) i7-3820 CPU @ 3.60GHz"
        }
    }, 
    "end": "1403858683.743105378", 
    "guest": {
        "bridge": "bridge2", 
        "image": {
            "name": "net-rcu", 
            "apps.version": "19a345fef3902a7654741c4afc760add51c65127", 
            "osv.version": "v0.09-261-g803bf2c", 
            "webapp.version": "45dc36acf79d7702d0a0b2b266d8e0e56fb9083e", 
            "os": "osv", 
            "osv.sha1": "803bf2ccda9a2e7c14c1248218c0e47f76553878"
        }, 
        "cpus": 4, 
        "memsize": "4g"
    }, 
    "tomcat": {
        "uname": "Linux muninn.cloudious 3.14.7-200.fc20.x86_64 #1 SMP Wed Jun 11 22:38:05 UTC 2014 x86_64 x86_64 x86_64 GNU/Linux", 
        "hostname": "muninn.cloudious", 
        "cpu": {
            "n_cores": "8", 
            "model": " Intel(R) Core(TM) i7-4770 CPU @ 3.40GHz"
        }
    }, 
    "start": "1403858621.435906001", 
    "ping": "rtt min/avg/max/mdev = 0.281/0.345/0.465/0.086 ms", 
    "wrk": {
        "latency": {
            "max": 24.54, 
            "unit": "ms"
        }, 
        "errors": 0, 
        "cmdline": "wrk --latency -t4 -c128 -d1m http://192.168.2.53:8081/servlet/json", 
        "throughput": "62518.26", 
        "duration": "1m", 
        "nr_connections": "128", 
        "nr_threads": "4"
    }, 
    "warmup_start": "1403858559.137378703", 
    "qemu.version": "1.6.2"
}
```

These properties can be later used for grouping in `report.py stats -g <attr1> -g <attr2>`.

# Reporting

You can list all completed tests with `report.py list`, eg:

```sh
$ ./report.py list
ID            OS     IMAGE              OS.VERSION         TIME                ERR THROUGHPUT
1403813181.04 osv    master             v0.09-260-g79c13c3 2014.06.26 22:06:21 0   59329.37
1403813520.82 osv    hacks              v0.09-267-g64ff688 2014.06.26 22:12:01 0   75272.54
1403813689.76 osv    master             v0.09-260-g79c13c3 2014.06.26 22:14:49 0   62154.05
```

You can print a statistics chart like this:
```sh
$ ./report.py stats -g guest/image/osv.version -g guest/image/os
throughput
======

                                   name        avg          stdev             min        max count
          ('v0.09-260-g79c13c3', 'osv')   61473.88    +0.0% 1221.29      59329.37   62497.05     6
          ('v0.09-261-g803bf2c', 'osv')   61459.40          995.64       60069.00   62548.94     7
          ('v0.09-267-g64ff688', 'osv')   76485.82   +24.4% 1379.49      74769.99   78256.17     7
```

Only results without errors are considered.

The `-g` arguments determine how results are grouped. The values passed are attribute locators. The attributes come from `test.properties` file. You can group using any attribute set.
