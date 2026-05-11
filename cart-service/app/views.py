from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer


class HealthCheck(APIView):
    def get(self, request):
        return Response({"service": "cart-service", "status": "ok"})

class CartCreate(APIView):
    def get(self, request):
        carts = Cart.objects.all()
        serializer = CartSerializer(carts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CartSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data) # [cite: 272]
        return Response(serializer.errors, status=400)

class AddCartItem(APIView):
    def post(self, request):
        book_id = request.data.get("book_id")
        cart_id = request.data.get("cart")
        quantity = request.data.get("quantity", 1)

        if not cart_id or not book_id:
            return Response({"error": "cart and book_id are required"}, status=400)

        cart_item = CartItem.objects.filter(cart_id=cart_id, book_id=book_id).first()
        if cart_item:
            cart_item.quantity += quantity
            cart_item.save()
            serializer = CartItemSerializer(cart_item)
            return Response(serializer.data)
        else:
            serializer = CartItemSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)


class CartItemDetail(APIView):
    def put(self, request, item_id):
        try:
            cart_item = CartItem.objects.get(id=item_id)
        except CartItem.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=404)

        serializer = CartItemSerializer(cart_item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, item_id):
        try:
            cart_item = CartItem.objects.get(id=item_id)
        except CartItem.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=404)

        cart_item.delete()
        return Response(status=204)

class ViewCart(APIView):
    def get(self, request, customer_id):
        # Tìm giỏ hàng theo ID khách hàng
        try:
            cart = Cart.objects.get(customer_id=customer_id)
            # Lấy tất cả các món hàng trong giỏ đó
            items = CartItem.objects.filter(cart=cart)
            serializer = CartItemSerializer(items, many=True)
            return Response({
                "customer_id": customer_id,
                "cart_id": cart.id,
                "items": serializer.data
            })
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=404)