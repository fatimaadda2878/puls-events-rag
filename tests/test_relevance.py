from app.rag import RAGService
def test_relevance_conversion():
 assert RAGService.relevance_from_l2(0)==1
 assert RAGService.relevance_from_l2(1)==0.5
 assert RAGService.relevance_from_l2(2)==0
