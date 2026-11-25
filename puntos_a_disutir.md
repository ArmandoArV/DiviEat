- Como hacemos auth
    cuando generamos un codigo QR para meterte en la pagina a ese ID va a estar relacionada la mesa
    - Mesa
        - SessionID _id
        - menu {
            - item
            - quantity
            - price per item
            - total
            - paid float
            - left to pay float
        }
        - table int
        - total float
        - left to pay (whole table)
        - tip {
            amount 
            percentage
        }
        - payment {
            transaction_id pey_id
            timestamp
            _id
        }
        timestamp: Date()
        status: Pending - Paying - Payed
    Mesa tiene menu y otros metadats

    Cuando se genera el qr

    // Obtener la cantidad de mesas activas
    db.tales.find({status: "Pending", status: "Paying"},{_id: 0, table: 1}).count()
    //ventas del turno
    db.tables.aggregate([
        $match: {
            timestamp: hoy xd,
            status: "Payed"
        },
        $group : { _id: null, $sum: {"$total"}}
    ])

    db.tables.find({table: 2})