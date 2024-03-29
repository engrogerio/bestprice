import logging
import json

import psycopg2



logger = logging.getLogger(__name__)


def exists_key(key, conn) -> bool:
    rows = []
    cursor = conn.cursor()
    cursor.execute(f"SELECT count(*) FROM cfe_header where access_key='{key}'")
    rows = cursor.fetchall()
    print('***',key, rows[0][0] == 0)
    return False if rows[0][0] == 0 else True

def insert_header(data:dict, conn)-> int:
    cursor = conn.cursor()
    query = "INSERT INTO cfe_header (cfeid, access_key, purchase_date, place_name, address, city) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"
    cursor.execute(query, (data['cfeid'], data['access_key'], data['purchase_date'], data['place_name'], data['address'], data['city']))
    inserted_id = cursor.fetchone()[0]
    conn.commit()
    return inserted_id

def insert_item(header_id, data_list:list, conn)-> int:
    # data = data_list[0]
    cursor = conn.cursor()
    query = """INSERT INTO cfe_item (item, description, qtty, unit, liquid_price,
    aditional_info, product_code, gtin_code,
    ncm_code,unit_price, gross_price, calc_rule, discount,
    icms_value, pis_value, pis_st_value, cofins_value, confins_st_value,
    issqn_value, total_tax_value, purchase_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """

    for data in data_list:
        cursor.execute(
            query, 
            (
                data['item'],
                data['description'],
                data['qtty'],
                data['unit'],
                data['liquid_price'],
                data['aditional_info'],
                data['product_code'],
                data['gtin_code'],
                data['ncm_code'],
                data['unit_price'],
                data['gross_price'],
                data['calc_rule'],
                data['discount'],
                data['icms_value'],
                data['pis_value'],
                data['pis_st_value'],
                data['cofins_value'],
                data['confins_st_value'], 
                data['issqn_value'],
                data['total_tax_value'],
                header_id
            )
        )
        inserted_id = cursor.fetchone()[0]
        conn.commit()
    return inserted_id

def is_product_on_db(gtin:str, conn) -> bool:
    cursor = conn.cursor()
    query = f"SELECT 1 FROM cfe_product WHERE gtin = '{gtin}'"
    try:
        cursor.execute(query)
    except Exception as ex:
        logger.error(ex)
        return False
    response = cursor.fetchone()
    return response

def insert_product_json(gtin, product_data:dict, conn)-> int:
    """
    Insert one row of product data on the product table
    """
    cursor = conn.cursor()
    query = f"insert into public.cfe_product(data, gtin) values('{ json.dumps(product_data)}', '{gtin}'::jsonb) RETURNING id"
    print(query)
    cursor.execute(query)
    inserted_id = cursor.fetchone()[0]
    conn.commit()
    return inserted_id

def insert_products(item_data:dict, product_api, conn):
    """
        Checks the just inserted items for new products. 
        If there is a new product on items table, insert on products.
    """
    def is_gtin_valid(gtin):
        return gtin.isnumeric()
    
    for item in item_data:
        print('Inserting: ', item)
        try:
            gtin = item['gtin_code']
        except:
            gtin = item
        if is_gtin_valid(gtin) and not is_product_on_db(gtin, conn):
            logger.info(f'API call for get product for {gtin}...')
            # insert data related to product
            try:
                product_data = product_api.get_data_for_gtin(gtin)
                print('****', json.dumps(product_data))
                if json.dumps(product_data) == '{"message": "Limite de requests excedido"}':
                    raise Exception('Limite de chamadas da API for excedido.')
                
                product_id = insert_product_json(gtin, product_data, conn)
                logger.info(f'Produto {product_id} inserido!')
            except (psycopg2.errors.InvalidTextRepresentation, psycopg2.errors.InFailedSqlTransaction) as ex:
                logger.warning(f'Produto {item} não foi inserido. {ex}')
                continue
            except Exception as ex:
                logger.exception(f'Produto {item} não foi inserido devido a um erro não esperado: {ex}')
                continue