from fastapi import APIRouter, HTTPException

from schemas import CrearTicketRequest
from services.crear_tickets import crear_ticket
from services.consultar_tickets import consultar_tickets
from services.actualizar_tickets import actualizar_ticket

router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"]
)


@router.post("/", status_code=201)
def registrar_ticket(datos: CrearTicketRequest):

    try:

        # 1. Convertir los datos del ticket a diccionario
        datos_ticket = datos.ticket.model_dump()

        # 2. Convertir fecha a formato compatible con MariaDB
        if datos_ticket["fecha_compra"] is not None:

            datos_ticket["fecha_compra"] = (
                datos_ticket["fecha_compra"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

        # 3. Ejecutar el CREATE
        resultado = crear_ticket(
            datos=datos_ticket,
            id_usuario=datos.id_usuario
        )

        # 4. Respuesta de la API
        return {
            "success": True,
            "mensaje": "Ticket registrado correctamente",
            "resultado": resultado
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except ConnectionError as error:

        raise HTTPException(
            status_code=503,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Error al registrar ticket: {str(error)}"
        )


# =====================================
# GET: CONSULTAR TODOS LOS TICKETS
# =====================================

@router.get("/")
def obtener_tickets():

    try:

        resultado = consultar_tickets()

        return {
            "success": True,
            "mensaje": "Tickets consultados correctamente",
            "total": len(resultado),
            "tickets": resultado
        }

    except ConnectionError as error:

        raise HTTPException(
            status_code=503,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar tickets: {str(error)}"
        )


# =====================================
# GET: CONSULTAR UN TICKET POR ID
# =====================================

@router.get("/{id_ticket}")
def obtener_ticket(id_ticket: int):

    try:

        resultado = consultar_tickets(id_ticket)

    except ConnectionError as error:

        raise HTTPException(
            status_code=503,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar ticket: {str(error)}"
        )

    if not resultado:

        raise HTTPException(
            status_code=404,
            detail="Ticket no encontrado"
        )

    return {
        "success": True,
        "mensaje": "Ticket encontrado",
        "resultado": resultado[0]
    }


# =====================================
# PUT: ACTUALIZAR TICKET
# =====================================

@router.put("/{id_ticket}")
def modificar_ticket(
    id_ticket: int,
    datos: CrearTicketRequest
):

    try:

        # 1. Convertir ticket a diccionario

        datos_ticket = datos.ticket.model_dump()

        # 2. Convertir fecha

        if datos_ticket["fecha_compra"] is not None:

            datos_ticket["fecha_compra"] = (
                datos_ticket["fecha_compra"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

        # 3. Ejecutar UPDATE

        resultado = actualizar_ticket(
            id_ticket=id_ticket,
            datos=datos_ticket
        )

        # 4. Respuesta

        return {
            "success": True,
            "mensaje": "Ticket actualizado correctamente",
            "resultado": resultado
        }

    except LookupError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except ConnectionError as error:

        raise HTTPException(
            status_code=503,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar ticket: {str(error)}"
        )