import os
import csv
import dedupe

def readData(filename):
    """
    Remap columns for the following cases:
    - Lat and Long are mapped into a single LatLong tuple
    - Class and Coauthor are stored as delimited strings but mapped into
      tuples
    """

    data_d = {}
    with open(filename, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            row = dict((k, v.lower()) for k, v in row.items())
            if row['Title'] == '':
                row['Title'] = None
            if row['Authors'] == '':
                row['Authors'] = None
            if row['Abstract'] == '':
                row['Abstract'] = None
            if row['Source'] == '':
                row['Source'] = None
            if row['DatePublished'] == '':
                row['DatePublished'] = None

            data_d[idx] = row

    return data_d

if __name__ == '__main__':
    
    input_file = 'entity-resolution/training-data-publications.csv'
    output_file = 'entity-resolution/training-data-publications-output.csv'
    settings_file = 'entity-resolution/publications-settings.json'
    training_file = 'entity-resolution/publications-training.json'

    print('importing data ...')
    data_d = readData(input_file)

    # ## Training

    if os.path.exists(settings_file):
        print('reading from', settings_file)
        with open(settings_file, 'rb') as sf:
            deduper = dedupe.StaticDedupe(sf, num_cores=2)

    else:
        # Define the fields dedupe will pay attention to
        fields = [
            {'field': 'Title',
             'variable name': 'Title',
             'type': 'String'},
            {'field': 'Authors',
             'variable name': 'Authors',
             'type': 'String',
             'has missing': True},
            {'field': 'Abstract',
             'variable name': 'Abstract',
             'type': 'String',
             'has missing': True},
            {'field': 'DatePublished',
             'variable name': 'DatePublished',
             'type': 'String',
             'has missing': True},
        ]

        # Create a new deduper object and pass our data model to it.
        deduper = dedupe.Dedupe(fields, num_cores=2)

        # If we have training data saved from a previous run of dedupe,
        # look for it an load it in.
        if os.path.exists(training_file):
            print('reading labeled examples from ', training_file)
            with open(training_file) as tf:
                deduper.prepare_training(data_d, training_file=tf)
        else:
            deduper.prepare_training(data_d)

        # ## Active learning

        # Starts the training loop. Dedupe will find the next pair of records
        # it is least certain about and ask you to label them as duplicates
        # or not.

        # use 'y', 'n' and 'u' keys to flag duplicates
        # press 'f' when you are finished
        print('starting active labeling...')
        dedupe.console_label(deduper)

        deduper.train()

        # When finished, save our training away to disk
        with open(training_file, 'w', encoding="utf-8", newline='') as tf:
            deduper.write_training(tf)

        # Save our weights and predicates to disk.  If the settings file
        # exists, we will skip all the training and learning next time we run
        # this file.
        with open(settings_file, 'wb', encoding="utf-8", newline='') as sf:
            deduper.write_settings(sf)

    clustered_dupes = deduper.partition(data_d, 0.5)

    print('# duplicate sets', len(clustered_dupes))

    # ## Writing Results

    # Write our original data back out to a CSV with a new column called
    # 'Cluster ID' which indicates which records refer to each other.

    cluster_membership = {}
    for cluster_id, (records, scores) in enumerate(clustered_dupes):
        for record_id, score in zip(records, scores):
            cluster_membership[record_id] = {
                "Cluster ID": cluster_id,
                "confidence_score": score
            }

    with open(output_file, 'w', encoding="utf-8", newline='') as f_output, open(input_file, encoding="utf-8") as f_input:

        reader = csv.DictReader(f_input)
        fieldnames = ['Cluster ID', 'confidence_score'] + reader.fieldnames

        writer = csv.DictWriter(f_output, fieldnames=fieldnames)
        writer.writeheader()

        for row_id, row in enumerate(reader):
            row.update(cluster_membership[row_id])
            writer.writerow(row)
