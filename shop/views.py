from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from shop.forms import OrderForm
from shop.models import Cart, Category, Product


# 아직 사용하지 않는 부분입니다.
def user_verification(func):
    def wrap(request, *args, **kwargs):
        session_user = User.objects.get(pk=kwargs["pk"])
        request_user = request.user

        if session_user != request_user:
            return HttpResponseForbidden()

        return func(request, *args, **kwargs)

    return wrap


def index(request):
    products = Product.objects.order_by("-pub_date")
    categories = Category.objects.all()
    ranked_products = products.order_by("-hit")[:4]

    context = {
        "products": products,
        "categories": categories,
        "ranked_products": ranked_products,
    }

    return render(request, "shop/index.html", context)


def show_category(request, category_id):
    categories = Category.objects.all()
    category = categories.get(id=category_id)

    products = Product.objects.filter(category=category)
    sorted_products = products.order_by("pub_date")
    ranked_products = products.order_by("-hit")[:4]

    try:
        page = int(request.GET.get("page", 1))
    except ValueError:
        page = 1

    paginator = Paginator(sorted_products, 8)
    products = paginator.get_page(page)

    context = {
        "categories": categories,
        "category": category,
        "products": products,
        "ranked_products": ranked_products,
    }

    return render(request, "shop/category.html", context)


def product_detail(request, product_id):
    categories = Category.objects.all()
    product = get_object_or_404(Product, id=product_id)

    product.hit += 1
    product.save()
    quantity_list = list(range(1, product.quantity + 1))

    context = {
        "quantity_list": quantity_list,
        "product": product,
        "category": product.category,
        "categories": categories,
    }

    return render(request, "shop/product_detail.html", context)


@login_required
def view_cart(request, pk):
    user = User.objects.get(pk=pk)
    cart_list = Cart.objects.filter(user=user)
    item_price_sum = sum(
        map(lambda item: item.quantity * item.products.price, cart_list)
    )

    try:
        page = int(request.GET.get("page", 1))
    except ValueError:
        page = 1

    paginator = Paginator(cart_list, 10)
    cart = paginator.get_page(page)

    context = {
        "user": user,
        "cart": cart,
        "item_price_sum": item_price_sum,
    }

    return render(request, "shop/cart.html", context)


@login_required
def delete_cart(request, pk):
    if request.method == "POST":
        user = request.user
        product_id = request.POST.get("product")

        if product_id:
            product = Product.objects.get(id=int(product_id))
            Cart.objects.get(user=user, products=product).delete()

        return redirect("shop:cart", user.pk)


@login_required
def add_to_cart(request, pk):
    if request.method == "POST":
        user = request.user
        product = Product.objects.get(pk=pk)
        quantity = int(request.POST.get("quantity"))
        cart_item = Cart.objects.filter(user=user, products=product).first()

        if cart_item:
            cart_item.quantity = min(cart_item.quantity + quantity, product.quantity)
            cart_item.save()
        else:
            Cart.objects.create(user=user, products=product, quantity=quantity)

        return redirect("shop:cart", user.pk)


@login_required
def pay(request, pk):
    if request.method == "POST":
        quantity = int(request.POST.get("quantity"))
        product = get_object_or_404(Product, pk=pk)
        user = request.user
        categories = Category.objects.all()

        initial = {"name": product.name, "amount": product.price, "quantity": quantity}

        form = OrderForm(request.POST, initial=initial)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = user
            order.quantity = quantity
            order.products = product
            order.save()
            return redirect("shop:order_list", user.pk)
        else:
            form = OrderForm(initial=initial)

        context = {
            "form": form,
            "quantity": quantity,
            "iamport_shop_id": "iamport",
            "user": user,
            "product": product,
            "categories": categories,
        }

        return render(request, "shop/order_pay.html", context)
