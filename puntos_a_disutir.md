- Como hacemos auth
    cuando generamos un codigo QR para meterte en la pagina a ese ID va a estar relacionada la mesa
    - Mesa
        - SessionID _id
        - menu [
            - item {
                - name
                - quantity
                - price per item
                - price left to pay 
                - total
                - total payed
                - status: Pending - Paying - Payed
            }
        ]
        - table int
        - total float
        - left to pay (whole table)
        - tip {
            amount 
            percentage
        }
        - payments [
            payment {
            "amount": 150,
            "apiKeyId": "01M3QMMR6X9CBVDY1SF3G8QWNW",
            "bankAccountId": "01JBAVWE4NS5TGXHWGMX3KH23Q",
            "codiQrId": "35a13c183a",
            "concept": "(dev) Order 345",
            "datePaid": 1790724818,
            "metadata": {
                "clabe": "000000000000000000",
                "bankCode": 40012,
                "accountType": 40,
                "description": "(dev) Order 345",
                "trackingKey": "0192191042",
                "externalMetadata": {
                "orderId": "12345",
                "customerEmail": "customer@example.com"
                }
            },
            "numRef": "34567",
            "transactionId": "01M3QR8H0RH0XBCKYYD242YXNV",
            "type": "codi.qr.payment_received"
            },
            {
            "amount": 150,
            "apiKeyId": "01M3QMMR6X9CBVDY1SF3G8QWNW",
            "bankAccountId": "01JBAVWE4NS5TGXHWGMX3KH23Q",
            "codiQrId": "35a13c183a",
            "concept": "(dev) Order 345",
            "datePaid": 1790724818,
            "metadata": {
                "clabe": "000000000000000000",
                "bankCode": 40012,
                "accountType": 40,
                "description": "(dev) Order 345",
                "trackingKey": "0192191042",
                "externalMetadata": {
                "orderId": "12345",
                "customerEmail": "customer@example.com"
                }
            },
            "numRef": "34567",
            "transactionId": "01M3QR8H0RH0XBCKYYD242YXNV",
            "type": "codi.qr.payment_received"
            },
            {
            "amount": 150,
            "apiKeyId": "01M3QMMR6X9CBVDY1SF3G8QWNW",
            "bankAccountId": "01JBAVWE4NS5TGXHWGMX3KH23Q",
            "codiQrId": "35a13c183a",
            "concept": "(dev) Order 345",
            "datePaid": 1790724818,
            "metadata": {
                "clabe": "000000000000000000",
                "bankCode": 40012,
                "accountType": 40,
                "description": "(dev) Order 345",
                "trackingKey": "0192191042",
                "externalMetadata": {
                "orderId": "12345",
                "customerEmail": "customer@example.com"
                }
            },
            "numRef": "34567",
            "transactionId": "01M3QR8H0RH0XBCKYYD242YXNV",
            "type": "codi.qr.payment_received"
            },
            {
            "amount": 150,
            "apiKeyId": "01M3QMMR6X9CBVDY1SF3G8QWNW",
            "bankAccountId": "01JBAVWE4NS5TGXHWGMX3KH23Q",
            "codiQrId": "35a13c183a",
            "concept": "(dev) Order 345",
            "datePaid": 1790724818,
            "metadata": {
                "clabe": "000000000000000000",
                "bankCode": 40012,
                "accountType": 40,
                "description": "(dev) Order 345",
                "trackingKey": "0192191042",
                "externalMetadata": {
                "orderId": "12345",
                "customerEmail": "customer@example.com"
                }
            },
            "numRef": "34567",
            "transactionId": "01M3QR8H0RH0XBCKYYD242YXNV",
            "type": "codi.qr.payment_received"
            },

        ]
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
    db.tables.find({_id: xxxxxxxxxxxx})

    // status de las mesas
    db.tables.find()



    user {
        name
        email
        role
        password
    }

    db.table.find({table: 54}, {"payments": 1, table: 1, _id: 0})