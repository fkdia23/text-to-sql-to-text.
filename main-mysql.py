import gradio as gr
from openai import OpenAI
import mysql.connector

# Configuration OpenAI
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"  # Remplacez par votre clé API OpenAI
)

# Configuration de la base de données MySQL
db_config = {
    "host": "localhost",  # Adresse du serveur MySQL
    "user": "root",
    "port": 3306,       # Nom d'utilisateur MySQL
    "password": "root",   # Mot de passe MySQL
    "database": "chinebook"  # Nom de la base de données
}

# Fonction pour se connecter à MySQL
def connect_to_db():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except mysql.connector.Error as e:
        return f"Erreur de connexion à MySQL : {e}"

# Générer une requête SQL avec OpenAI
def generate_query(user_prompt):
    try:
        # Prompt pour guider l'API OpenAI
        prompt_system = """
        You are an SQL expert specialized in optimizing and analyzing music databases. Your expertise covers:
                - Query optimization for maximum performance
                - Complex data manipulation with multiple joins
                - Statistical data aggregation and analysis
                - SQL best practices

            1. Music Content Management:
                - 'Artist' (ArtistId [PK], Name)
                - 'Album' (AlbumId [PK], Title, ArtistId [FK])
                - 'Track' (TrackId [PK], Name, AlbumId [FK], MediaTypeId [FK], GenreId [FK], Composer, Milliseconds, Bytes, UnitPrice)
                - 'Genre' (GenreId [PK], Name)
                - 'MediaType' (MediaTypeId [PK], Name)

            2. Playlist System:
                - 'Playlist' (PlaylistId [PK], Name)
                - 'PlaylistTrack' (PlaylistId [PK/FK], TrackId [PK/FK])

            3. Sales and Customer Data:
                - 'Customer' (CustomerId [PK], FirstName, LastName, Company, Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId [FK])
                - 'Employee' (EmployeeId [PK], LastName, FirstName, Title, ReportsTo [FK], BirthDate, HireDate, Address, City, State, Country, PostalCode, Phone, Fax, Email)
                - 'Invoice' (InvoiceId [PK], CustomerId [FK], InvoiceDate, BillingAddress, BillingCity, BillingState, BillingCountry, BillingPostalCode, Total)
                - 'InvoiceLine' (InvoiceLineId [PK], InvoiceId [FK], TrackId [FK], UnitPrice, Quantity)

            KEY RELATIONSHIPS:
            - Artists have many Albums
            - Albums contain many Tracks
            - Tracks belong to Genres and MediaTypes
            - Tracks can be in multiple Playlists (via PlaylistTrack)
            - Customers place Orders (Invoices)
            - Invoices contain InvoiceLines (individual track purchases)
            - Employees can be Support Representatives for Customers
            - Employees can report to other Employees                  - Complex data manipulation with multiple joins
                          - Statistical data aggregation and analysis
                          - SQL best practices
                          Main tables and their relationships:
              DATABASE SCHEMA:

        An example of respons: 

        "SELECT c.customer_id, c.name, c.email, SUM(o.total_amount) as total_spent FROM customers c INNER JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.name, c.email HAVING SUM(o.total_ammount) > 1000 ORDER BY total_spent DESC;"
        """

        # Appel à l'API OpenAI
        completion = client.chat.completions.create(
            model="meta-llama/llama-3.1-70b-instruct:free",
            messages=[
      {
          "role": "system",
          "content": """
                        You are an SQL expert specialized in optimizing and analyzing music databases. Your expertise covers:
                          - Query optimization for maximum performance
                          - Complex data manipulation with multiple joins
                          - Statistical data aggregation and analysis
                          - SQL best practices
                          Main tables and their relationships:
                      """
                        + prompt_system +

                      """
                          The first object with "role": "system" should describe the task of an SQL assistant.
                          The second object with "role": "user" should contain a natural language request related to SQL databases.
                          The third object with "role": "assistant" should provide an SQL query that satisfies the request from the previous object.
                          Create at least 1 sets of conversations in this format in the JSON file. Here's an example for reference:      
                             SELECT c.customer_id, c.name, c.email, SUM(o.total_amount) as total_spent FROM customers c INNER JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.name, c.email HAVING SUM(o.total_ammount) > 1000 ORDER BY total_spent DESC;"}
                           **
                        Your task: Generate precise and optimized SQL queries in response to user requests. Provide only the SQL query, without explanatory text."""
      },
              {
          "role": "user",
          "content": f""" generate only sql script to {user_prompt}"""
      },
      {
        "role": "assistant",
        "content": "SELECT c.customer_id, c.name, c.email, SUM(o.total_amount) as total_spent FROM customers c INNER JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.name, c.email HAVING SUM(o.total_amount) > 1000 ORDER BY total_spent DESC;"
      }
    ],
            temperature= 0,
            top_p=1,
        )
        sql_query = completion.choices[0].message.content.strip()
        return sql_query
    except Exception as e:
        return f"Erreur lors de la génération de la requête SQL : {e}"

# Exécuter une requête SQL dans MySQL
def execute_query(sql_query):
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute(sql_query)
        
        # Gestion des résultats SELECT
        if sql_query.strip().lower().startswith("select"):
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]  # Colonnes des résultats
            formatted_result = [dict(zip(columns, row)) for row in result]
            return formatted_result
        else:
            connection.commit()
            return "Requête exécutée avec succès."
    except mysql.connector.Error as e:
        return f"Erreur lors de l'exécution de la requête : {e}"
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Interface Gradio pour la génération et l'exécution de requêtes SQL
def handle_generate_query(user_prompt):
    return generate_query(user_prompt)

def handle_execute_query(sql_query):
    result = execute_query(sql_query)
    if isinstance(result, list):  # Résultats d'une requête SELECT
        return "\n".join([str(row) for row in result])
    return result

# Construire l'interface Gradio
with gr.Blocks() as demo:
    gr.Markdown("## Génération et Exécution de Requêtes SQL avec OpenAI et MySQL")

    # Génération de requête SQL
    with gr.Row():
        user_prompt = gr.Textbox(label="Commande en langage naturel", placeholder="Exemple : Donne-moi les clients ayant dépensé plus de 1000€")
        generate_btn = gr.Button("Générer Requête SQL")
    sql_query_box = gr.Textbox(label="Requête SQL générée", interactive=True)

    # Exécution de requête SQL
    with gr.Row():
        execute_btn = gr.Button("Exécuter Requête SQL")
        result_box = gr.Textbox(label="Résultats de la requête", interactive=False)

    # Actions des boutons
    generate_btn.click(handle_generate_query, inputs=user_prompt, outputs=sql_query_box)
    execute_btn.click(handle_execute_query, inputs=sql_query_box, outputs=result_box)

# Lancer l'interface
demo.launch()
