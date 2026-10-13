from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Page-number pagination that lets a client ask for a larger page (e.g. a whole class roster)."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200
