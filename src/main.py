import os
import pymongo

from flask import Flask, make_response, request, jsonify
from scipy.stats.stats import pearsonr

app = Flask(__name__)


@app.route('/calculate', methods=['POST'])
def calculate():
    request_data = request.json
    x_raw = request_data['data']['x']
    y_raw = request_data['data']['y']

    if not x_raw or not y_raw:
        return make_response(jsonify({'error': 'No data found for x/y'}), 400)

    x_dict = dict(map(lambda item: (item['date'], item['value']), x_raw))
    y_dict = dict(map(lambda item: (item['date'], item['value']), y_raw))

    x, y = [], []
    for dt in x_dict:
        if dt in y_dict:
            x.append(x_dict[dt])
            y.append(y_dict[dt])

    corr, p_value = pearsonr(x, y)

    client = pymongo.MongoClient(os.environ.get('MONGODB_HOSTNAME'), 27017)
    db = client.correlation_db
    coll = db.correlation

    new_record = {
        'user_id': int(request_data['user_id']),
        'x_data_type': request_data['data']['x_data_type'],
        'y_data_type': request_data['data']['y_data_type'],
        'correlation': {
            'value': corr,
            'p_value': p_value
        }
    }

    existing_filter = new_record.copy()
    existing_filter.pop('correlation')
    # Updates record for the user and the data types
    # Inserts new record if no data found

    coll.replace_one(existing_filter, new_record, upsert=True)

    return make_response(jsonify({'status': 'OK'}))


@app.route('/correlation',  methods=['GET'])
def correlation():

    user_id = request.args.get('user_id', 0)
    x_data_type = request.args.get('x_data_type', '')
    y_data_type = request.args.get('y_data_type', '')

    client = pymongo.MongoClient(os.environ.get('MONGODB_HOSTNAME'), 27017)
    db = client.correlation_db
    coll = db.correlation
    db_filter = {
        'user_id': int(user_id),
        'x_data_type': x_data_type,
        'y_data_type': y_data_type
    }
    result = coll.find_one(filter=db_filter)

    if not result:
        return make_response(jsonify({'error': 'Not found'}), 404)
    result.pop('_id')

    return make_response(jsonify(result))


def main():
    app.run(host='0.0.0.0', port='8000')


if __name__ == '__main__':
    main()
