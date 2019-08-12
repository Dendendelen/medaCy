"""
MedaCy CLI Setup
"""
import argparse
import logging
from datetime import datetime
import time
import importlib

from medacy.data import Dataset
from medacy.ner import Model
from medacy.ner import SpacyModel

def setup(args):
    """
    Sets up dataset and pipeline/model since it gets used by every command.

    :param args: Argparse args object.
    :return dataset, model: The dataset and model objects created.
    """
    dataset = Dataset(args.dataset)

    pipeline = None

    if args.pipeline == 'spacy':
        logging.info('Using spacy model')

        model = SpacyModel(spacy_model_name=args.spacy_model, cuda=args.cuda)

    else:
        #Parse the argument as a class name in module medacy.ner.pipelines
        module = importlib.import_module("medacy.ner.pipelines")
        pipeline_class = getattr(module, args.pipeline)
        logging.info('Using %s', args.pipeline)

        if args.word_embeddings is not None:
            pipeline = pipeline_class(word_embeddings=args.word_embeddings, cuda_device=args.cuda)
        else:
            pipeline = pipeline_class(cuda_device=args.cuda)

        model = Model(pipeline)

    return dataset, model

def train(args, dataset, model):
    """
    Used for training new models.

    :param args: Argparse args object.
    :param dataset: Dataset to use for training.
    :param model: Untrained model object to use.
    """
    if args.filename is None:
        response = input('No filename given. Continue without saving the model at the end? (y/n) ')
        if response.lower() == 'y':
            model.fit(dataset, asynchronous=args.asynchronous)
        else:
            print('Cancelling. Add filename with -f or --filename.')
    else:
        model.fit(dataset, args.asynchronous)
        model.dump(args.filename)

def predict(args, dataset, model):
    """
    Used for running predictions on new datasets.

    :param args: Argparse args object.
    :param dataset: Dataset to run prediction over.
    :param model: Trained model to use for predictions.
    """

    model.load(args.model_path)
    model.predict(
        dataset,
        prediction_directory=True,
        groundtruth_directory=True
    )

def cross_validate(args, dataset, model):
    """
    Used for running k-fold cross validations.

    :param args: Argparse args object.
    :param dataset: Dataset to use for training.
    :param model: Untrained model objec to use.
    """
    model.cross_validate(
        num_folds=args.k_folds,
        training_dataset=dataset,
        prediction_directory=True,
        groundtruth_directory=True,
        asynchronous=args.asynchronous
    )

def main():
    """
    Main function where initial argument parsing happens.
    """
    # Argparse setup
    parser = argparse.ArgumentParser(prog='medacy', description='Train and evaluate medaCy pipelines.')
    parser.add_argument('-p', '--print_logs', action='store_true', help='Use to print logs to console.')
    parser.add_argument('-pl', '--pipeline', default='ClinicalPipeline', help='Pipeline to use for training. Write the exact name of the class. Default medacy clinical pipeline.')
    parser.add_argument('-d', '--dataset', required=True, help='Directory of dataset to use for training.')
    parser.add_argument('-w', '--word_embeddings', help='Path to word embeddings.')
    parser.add_argument('-a', '--asynchronous', action='store_true', help='Use to make the preprocessing run asynchronously. Causes GPU issues.')
    parser.add_argument('-c', '--cuda', type=int, default=-1, help='Cuda device to use. -1 to use CPU.')
    parser.add_argument('-sm', '--spacy_model', default=None, help='SpaCy model to use as starting point.')
    subparsers = parser.add_subparsers()

    # Train arguments
    parser_train = subparsers.add_parser('train', help='Train a new model.')
    parser_train.add_argument('-f', '--filename', help='Filename to use for saved model.')
    parser_train.set_defaults(func=train)

    # Predict arguments
    parser_predict = subparsers.add_parser('predict', help='Run predictions on the dataset using a trained model.')
    parser_predict.add_argument('-m', '--model_path', required=True, help='Trained model to load.')
    parser_predict.set_defaults(func=predict)

    # Cross Validation arguments
    parser_validate = subparsers.add_parser('validate', help='Cross validate a model on a given dataset.')
    parser_validate.add_argument('-k', '--k_folds', default=5, type=int, help='Number of folds to use for cross-validation.')
    parser_validate.set_defaults(func=cross_validate)

    # Parse initial args
    args = parser.parse_args()

    # Logging
    logging.basicConfig(filename='medacy.log', format='%(asctime)-15s: %(message)s', level=logging.INFO)
    if args.print_logs:
        logging.getLogger().addHandler(logging.StreamHandler())
    start_time = time.time()
    current_time = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
    logging.info('\n\nSTART TIME: %s', current_time)

    # Run proper function
    dataset, model = setup(args)
    args.func(args, dataset, model)

    # Calculate/print end time
    end_time = time.time()
    current_time = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')
    logging.info('END TIME: %s', current_time)

    # Calculate/print time elapsed
    seconds_elapsed = end_time - start_time
    minutes_elapsed, seconds_elapsed = divmod(seconds_elapsed, 60)
    hours_elapsed, minutes_elapsed = divmod(minutes_elapsed, 60)

    logging.info('H:M:S ELAPSED: %d:%d:%d', hours_elapsed, minutes_elapsed, seconds_elapsed)

if __name__ == '__main__':
    main()
