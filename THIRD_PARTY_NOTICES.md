# Third-party notices

K-Audio integrates or can call third-party software, services and models. Their names do not imply endorsement of K-Audio.

## OmniVoice source code

The `omnivoice/` directory is derived from [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice), copyright its respective contributors (including Xiaomi Corp. notices present in source files), and is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).

Retain upstream copyright headers and a copy of the Apache-2.0 license when redistributing that directory or modifications of it. Modified files should carry a clear change notice as required by Apache-2.0.

## OmniVoice pretrained model

The weights are intentionally excluded from this repository. The current [official model card](https://huggingface.co/k2-fsa/OmniVoice) states that source code is Apache-2.0 while pretrained weights are licensed under CC-BY-NC because of training-data constraints.

## Higgs Audio 2 tokenizer

The tokenizer bundled with the downloaded model is intentionally excluded. Its license file identifies the **Boson Higgs Audio 2 Community License Agreement**, with additional attribution, acceptable-use and commercial conditions. Review the license distributed with the tokenizer before use or redistribution.

## Other dependencies and services

Packages in `requirements.txt`, FFmpeg, API providers and web services retain their own licenses and terms. Installing a dependency does not transfer its copyright to K-Audio. Users are responsible for complying with current terms, rate limits, content policies and applicable law.

## Content and voice rights

The repository includes default reference-voice profiles in `data/voices` for use by K-Audio. These audio and metadata files are not model weights and are not automatically covered by the Apache-2.0 software license. Voice, likeness, privacy and dataset rights may apply independently. Do not impersonate a person, redistribute a voice dataset, or use a voice commercially unless you have the necessary authorization and consent.

No rights are granted to crawl, reproduce, synthesize, publish or monetize third-party stories, translations, websites, music, images or video. Obtain authorization before use.
