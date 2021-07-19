# Arvada

A tool to infer grammars from an example set and a correctness oracle, that can be used for both generation and parsing tasks.

## Artifact for Replication

We provide a docker container that contains replication instructions for the experiments from Learning Highly Recursive Input Grammars, submitted to ASE'21, at [this link](https://drive.google.com/file/d/1DfPd0eb9YPUkPo4hsr35PQC6ChzZ7ob0/view?usp=sharing). The README in the docker container describes how to use the run scripts, as well as expected time to replicate the experiments

## Building

Requires python3 to run. Install the following two packages via pip to make sure everything runs:
```
$ pip3 install lark-parser
$ pip3 install tqdm
```

## Running Arvada

Suppose you have a directory containing a set of examples, `TRAIN_DIR`, and an oracle for a valid example, `ORACLE_CMD`. The restrictions on `ORACLE_CMD` are as follows:

- `ORACLE_CMD filename` should run the oracle on the file with name `filename`
- `ORACLE_CMD filename` should return 0 if the example in `filename` is valid, and an exit code greater than 0 if it is invalid. 

You can then run Arvada via:
```
$ python3 search.py external ORACLE_CMD TRAIN_DIR LOG_FILE
```
this will store the learned grammar as a pickled dictionary in `LOG_FILE.gramdict`, and some information about training in `LOG_FILE`.

If you also have a held-out test set in `TEST_DIR`, you can evaluate the precision and recall of the mined grammar with the utility `eval.py`. This utility also handily prints out the unpickled grammar. The provided `LOG_FILE` must match one generated by search.py, as this utility looks for `LOG_FILE.gramdict`. 
```
$ python3 eval.py external ORACLE_CMD TEST_DIR LOG_FILE [PRECISION_SET_SIZE]
```
The optional `PRECISION_SET_SIZE` argument specifies how many inputs to sample from the mined grammar to evaluate precision. It is 1000 by default.

Of course, if you do not have a held-out test set, you can still evaluate the precision of the mined grammar by using your training directory as test:
```
$ python3 eval.py external ORACLE_CMD TRAIN_DIR LOG_FILE [PRECISION_SET_SIZE]
```
The Recall should be 1.0 in this case.


## Minimal working example

The directory `bc-example` contains a minimal example of learning a calculator language from a set of example and the correctness oracle as the `bc` program running without syntax errors.

First ensure that [`bc`](https://www.gnu.org/software/bc/manual/html_mono/bc.html) is installed; it should come standard on most linux distributions. If everything works fine, the following command should run without error:
```
$ ./bc-example/bc-wrapper.sh bc-example/train_set/guide-0.ex
```

You can learn a grammar from the oracle `./bc-example/bc-wrapper` and the provided examples in `bc-example/train_set` as follows:
```
$ python3 search.py external .bc-example/bc-wrapper.sh bc-example/train_set bc-example.log
```
(this took around 20 seconds on our machine)

The grammar is stored as a pickled object in `bc-example.log.gramdict`. The `eval.py` utility will print out the grammar in `bc-example.log.eval` after running: 
```
$ python3 search.py external .bc-example/bc-wrapper.sh bc-example/test_set bc-example.log 100
```

Over 5 runs, we witnessed 4 runs with 1.0 Recall and 1.0 Precision, and 1 run with 0.95 Recall and 1.0 Precision.