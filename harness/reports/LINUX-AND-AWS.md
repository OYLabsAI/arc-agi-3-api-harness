# What Linux is needed for; where AWS fits

Linux is needed to validate the actual Kaggle execution target. It is not an independent
ARC rule requiring AWS. The ARC requirement is an automated Kaggle notebook with replaceable
data, permitted API access, full completion within 12 hours and its total cost ceiling.
[ARC verification policy](https://arcprize.org/policy).

**Recommended: run the private notebook directly in Kaggle's CPU Linux runtime.**
It needs Python 3.12, internet access for the pinned source/dependencies and OpenAI/ARC,
private outputs, an evaluator Kaggle account, and (for the paid pilot) the two API secrets.
No GPU is required by this harness: inference runs at OpenAI. First execute fixture mode,
then the authorized pilot. This directly resolves the Linux setup gate and starts resolving
the Kaggle gate. A complete measured API evaluation is still required for runtime/cost proof.

**AWS works for Linux validation or external compute.** A conservative starting configuration
for software validation is Ubuntu 24.04 LTS x86_64, Python 3.12, 2 vCPUs, 8 GiB RAM and 30 GiB
disk, with no GPU. These are engineering starting sizes, not measured minimum requirements.
Use a fresh non-root runtime, no mounted owner HOME, the supplied hash lock and private outputs.
Record region, AMI, instance type, runtime versions, setup time, logs, exit status and compute cost.
Official launch references: [Ubuntu on EC2](https://documentation.ubuntu.com/aws/aws-how-to/instances/launch-ubuntu-ec2-instance/)
and [EC2 boot automation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html).

An AWS-only evaluation does not satisfy the Kaggle notebook rule. If Kaggle delegates to AWS,
the notebook must also automate provisioning, invocation, metering and teardown using evaluator
credentials, include AWS charges in the global cap, and account for AWS as an evidence/data
recipient. Those AWS orchestration controls are NOT SATISFIED in this candidate. No evidence
currently shows AWS is necessary; adding it would increase the work required for compliance.

AWS access/account, region, compute spending limit and deployment are not configured. No cloud
resources have been provisioned or charged. The delivered Dockerfile/commands are preparation
artifacts; successful Linux execution evidence remains NOT SATISFIED until run.
