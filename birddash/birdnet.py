"""BirdNET-Analyzer wrappers.

Thin functional wrappers around birdnet-analyzer used for on-upload analysis
with the *global* BirdNET model. (The custom-classifier, dual-threshold
multi-species pipeline lives in birddash.detection.)

The heavy `birdnet_analyzer` import is deferred to call time so importing this
module stays cheap.
"""

from birddash import config


def analyze_upload(audio_rel_path, output_dir=None, min_conf: float = 0.05):
    """Run global BirdNET on a single uploaded recording, writing a CSV.

    `audio_rel_path` should be relative to config.BASE_DIR so BirdNET records
    the File column as "sample_audio/<name>", consistent with every other
    recording (required for selection + playback). Only the given file is
    analysed, so one unrelated bad recording can't abort a batch.
    """
    from birdnet_analyzer import analyze

    if output_dir is None:
        output_dir = config.BIRDNET_RESULTS_DIR

    analyze(
        audio_input=audio_rel_path,
        output=str(output_dir),
        min_conf=min_conf,
        rtype="csv",
        skip_existing_results=True,
    )
